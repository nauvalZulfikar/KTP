import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import math
from collections import defaultdict
import streamlit as st

# df, dfm, component_waiting_df, product_waiting_df, late_df
df = pd.read_excel('Product Details_v1.xlsx', sheet_name='P')
# Convert columns to appropriate types
df['Order Processing Date'] = pd.to_datetime(df['Order Processing Date'])
df['Promised Delivery Date'] = pd.to_datetime(df['Promised Delivery Date'])
df['Start Time'] = pd.NaT  # Initialize as empty datetime
df['End Time'] = pd.NaT  # Initialize as empty datetime
df['Status'] = ''  # Initialize the Status column

# Assign values to 'Status' column based on 'Process Type' using .loc[]
df.loc[df['Process Type'] == 'In House', 'Status'] = 'InProgress_In House'
df.loc[df['Process Type'] == 'Outsource','Status'] = 'InProgress_Outsource'

# Sort the data by Promised Delivery Date, Product Name, and Component order
df = df.sort_values(by=['Promised Delivery Date',
                        'Product Name',
                        'Components']).reset_index(drop=True)


# Define working hours and working days
WORK_HOURS_PER_DAY = 8
WORK_START = 9  # 9 AM
WORK_END = 17 + 1/60  # 5 PM
WEEKENDS = [5, 6]  # Saturday and Sunday

# Function to find the next valid working day
def next_working_day(current_date):
    while current_date.weekday() in WEEKENDS:  # Check if the day is a weekend
        current_date += timedelta(days=1)  # Move to the next day
    return current_date

# Function to adjust the Start Time and End Time in the schedule
def adjust_end_time_and_start_time(data):
    for idx, row in data.iterrows():
        # If the Start Time is at exactly 5:00 PM
        if row['Start Time'].hour == 17 and row['Start Time'].minute == 0 and row['Start Time'].second == 0:
            # Move the Start Time to 9:00 AM the next day
            new_end_time = row['Start Time'] + timedelta(days=1)
            new_end_time = new_end_time.replace(hour=9, minute=0, second=0)
            data.at[idx, 'Start Time'] = new_end_time

        # If the End Time is earlier than 9:00 AM
        elif row['End Time'].hour < 9:
            # Adjust the End Time to be exactly 9:00 AM on the same day
            data.at[idx, 'End Time'] = row['End Time'].replace(hour=9, minute=0, second=0)

    # Return the updated schedule
    return data

# Function to find gaps in the machine schedule
def find_gaps(machine_schedule):
    gaps = {}
    for machine, tasks in machine_schedule.items():
        tasks = sorted(tasks, key=lambda x: x[0])  # Sort tasks by start time
        gaps[machine] = []
        for i in range(len(tasks) - 1):
            current_end = tasks[i][1]
            next_start = tasks[i + 1][0]
            if next_start > current_end:
                gaps[machine].append((current_end, next_start))  # Record gap
    return gaps
  
def schedule_production_with_days(data):
    # We start by assuming there are tasks that need to be scheduled
    has_empty_rows = True
    # Keep trying to schedule tasks until all tasks have a Start and End Time
    while has_empty_rows:
        # This dictionary will track when each machine is free or busy
        machine_schedule = defaultdict(list)
        for machine in data['Machine Number'].unique():
          machine_schedule[machine].append(
              (data['Order Processing Date'].min().replace(hour=WORK_START, minute=0),
              data['Order Processing Date'].min().replace(hour=WORK_START, minute=0),
              None))

        # Initialize the last available time for each machine to 9:00 AM on the first day
        machine_last_end = {
            machine: next_working_day(data['Order Processing Date'].min().replace(hour=WORK_START, minute=0))
            for machine in data['Machine Number'].unique()
        }

        # Sort tasks by when they are due, their product name, and their component
        # # This helps ensure we prioritize the most urgent tasks
        # data = data.sort_values(by=['Promised Delivery Date', 'Product Name', 'Components']).reset_index(drop=True)

        # Go through each task, one by one
        for i in range(len(data)):
            # This helps ensure we prioritize the most urgent tasks
            data = data.sort_values(by=['Promised Delivery Date', 'Product Name', 'Components']).reset_index(drop=True)

            # Information about the current task
            component = data['Components'][i]  # Example: C1, C2, etc.
            product = data['Product Name'][i]  # Example: Product 1, Product 2
            machine = data['Machine Number'][i]  # The machine where the task is performed
            gap_start_time = None  # Start time if the task fits into a gap
            gap_end_time = None  # End time if the task fits into a gap
            fallback_start_time = None  # Backup start time
            fallback_end_time = None  # Backup end time
            full_start_time = None  # Final fallback start time
            full_end_time = None  # Final fallback end time

            # ==========================
            # OUTSOURCE SCHEDULING
            # ==========================
            # If this task is outsourced and uses an external machine
            if "C1" in component and machine == "OutSrc":
                # Start the task at 9:00 AM on the order processing date
                start_time = data['Order Processing Date'][i].replace(hour=WORK_START, minute=0)
                # Calculate how long the task will take
                run_time_minutes = data['Run Time (min/1000)'][i] * data['Quantity Required'][i] / 1000
                # Determine when the task will end
                end_time = adjust_to_working_hours_and_days(start_time, run_time_minutes)

                # Save the Start and End Times for this task
                data.at[i, 'Start Time'] = start_time
                data.at[i, 'End Time'] = end_time
                continue  # Move to the next task

            # ==========================
            # MACHINE SCHEDULING
            # ==========================
            # Look for earlier tasks for the same product
            same_product_prev = data.iloc[:i][data.iloc[:i]['Product Name'] == product]
            if not same_product_prev.empty:
                # If there are earlier tasks, start this task after the last one ends
                product_last_end = same_product_prev.iloc[-1]['End Time']
            else:
                # Otherwise, start after the order processing date
                product_last_end = data['Order Processing Date'][i]

            # ==========================
            # FIND GAPS
            # ==========================
            # Check if there are gaps in the machine's schedule
            gaps = find_gaps(machine_schedule)
            for gap_start, gap_end in gaps.get(machine, []):
                # Determine the earliest possible start time for the task
                # Ensure it starts after the previous component (if any) or product's last end time
                prev_component_end_time = data.iloc[:i][
                    (data.iloc[:i]['Product Name'] == product) &
                    (data.iloc[:i]['Components'] < component)
                ]['End Time'].max()

                # Use product's last end time if no previous component exists
                if pd.isna(prev_component_end_time):
                    prev_component_end_time = product_last_end

                # Enforce the dependency rule: Skip gaps that start before the previous component's end time
                adjusted_gap_start = max(gap_start, prev_component_end_time)
                if adjusted_gap_start >= gap_end:
                    continue  # Skip this gap entirely

                # Calculate how long the task will take
                run_time_minutes = data['Run Time (min/1000)'][i] * data['Quantity Required'][i] / 1000
                potential_end_time = adjust_to_working_hours_and_days(adjusted_gap_start, run_time_minutes)

                # ==========================
                # IF TASK FITS IN THE GAP
                # ==========================
                # Check if the task fits within the adjusted gap
                if potential_end_time <= gap_end:
                    # Task can fit in this gap
                    gap_start_time = adjusted_gap_start
                    gap_end_time = potential_end_time
                    break  # Exit the loop as the task is now scheduled

                # ==========================
                # IF NOT, SPLIT (FIRST)
                # ==========================
                # If the task does not fit, split it into smaller pieces
                available_minutes = (gap_end - adjusted_gap_start).total_seconds() / 60
                # set_end_time = min(run_time_minutes,available_minutes)
                producible_qty = (available_minutes / run_time_minutes) * data['Quantity Required'][i]

                # Update the task with the producible quantity
                remaining_task = data.iloc[i].to_frame().T.copy()
                data.at[i, 'Quantity Required'] = producible_qty

                # If there’s remaining work, create a new task for it
                if producible_qty > 0:
                    remaining_qty = remaining_task['Quantity Required'] - producible_qty
                    # remaining_task = data.iloc[i].copy()
                    remaining_task['Quantity Required'] = remaining_qty
                    remaining_task['Start Time'] = None
                    remaining_task['End Time'] = None
                    # Add the new task to the dataset
                    data = pd.concat([data, remaining_task], ignore_index=True)

                # Schedule the producible part of the task in this gap
                gap_start_time = adjusted_gap_start
                gap_end_time = gap_end
                break  # Exit the loop as the task is now partially scheduled


            # ==========================
            # IF NO GAPS
            # ==========================
            if gap_end_time is None:
                # Schedule the task to start after the machine's last available time
                fallback_start_time = max(product_last_end, machine_last_end[machine])
                run_time_minutes = data['Run Time (min/1000)'][i] * data['Quantity Required'][i] / 1000
                fallback_end_time = adjust_to_working_hours_and_days(fallback_start_time, run_time_minutes)

            # Calculate the final fallback times if everything else fails
            full_start_time = max(product_last_end, machine_last_end[machine])
            run_time_minutes = data['Run Time (min/1000)'][i] * data['Quantity Required'][i] / 1000
            full_end_time = adjust_to_working_hours_and_days(full_start_time, run_time_minutes)

            # Decide the final start and end times for the task
            start_time = gap_start_time if gap_start_time else fallback_start_time if fallback_start_time else full_start_time
            end_time = gap_end_time if gap_end_time else fallback_end_time if fallback_end_time else full_end_time

            # Update the machine schedule
            if machine != "OutSrc":
                machine_schedule[machine].append((start_time, end_time, i))
                machine_schedule[machine] = sorted(machine_schedule[machine], key=lambda x: x[0])
                machine_last_end[machine] = max(machine_last_end[machine], end_time)

            # Save the Start and End Times for the task
            data.at[i, 'Start Time'] = start_time
            data.at[i, 'End Time'] = end_time

        # Check if any tasks are still unscheduled
        has_empty_rows = data['Start Time'].isna().any() or data['End Time'].isna().any()

    data['Quantity Required'] = data['Quantity Required'].apply(lambda x:round(x))
    
    # Return the completed schedule
    return data

def calculate_gaps(dfm):
    loop_len = max(df['Product Name'].value_counts())
    dfm = df.groupby('Product Name', as_index=False).first().sort_values(by=['Promised Delivery Date', 'Start Time','End Time']).reset_index(drop=True)

    for x in range(1,loop_len+1):
      dfj = df.groupby('Product Name', as_index=False).nth(x).sort_values(by=['Promised Delivery Date', 'Start Time','End Time']).reset_index(drop=True)
      dfm = pd.concat([dfm, dfj]).sort_values(by=['Promised Delivery Date', 'Start Time']).reset_index(drop=True)

      # Calculate gaps based on machine usage
      dfm = dfm.sort_values(by=['Machine Number','Start Time','End Time']).reset_index(drop=True)
      machine_gaps = [0]
      machine_prev = [0]
      for i in range(len(dfm) - 1):
          if dfm['Machine Number'].iloc[i] == dfm['Machine Number'].iloc[i + 1]:
              gap = (dfm['Start Time'].iloc[i + 1] - dfm['End Time'].iloc[i]).total_seconds() / 60  # Minutes
              prev_m = dfm['UniqueID'][i]
          else:
              gap = 0
              prev_m = 0
          if dfm['Machine Number'].iloc[i] == 'OutSrc':
              gap = 0
          machine_gaps.append(gap)
          machine_prev.append(prev_m)
      dfm['machine_gaps'] = machine_gaps
      dfm['machine_prev'] = machine_prev

      # Calculate gaps based on product name and components
      dfm = dfm.sort_values(by=['Start Time','End Time','Product Name','Components',]).reset_index(drop=True)
      prod_comp_gaps = [0]
      prod_comp_prev = [0]
      for i in range(len(dfm) - 1):
          if dfm['Product Name'].iloc[i] == dfm['Product Name'].iloc[i + 1] and dfm['Components'].iloc[i] != dfm['Components'].iloc[i + 1]:
              gap = (dfm['Start Time'].iloc[i + 1] - dfm['End Time'].iloc[i]).total_seconds() / 60  # Minutes
              prev_pc = dfm['UniqueID'][i]
          else:
              gap = 0
              prev_pc = 0
          prod_comp_gaps.append(gap)
          prod_comp_prev.append(prev_pc)
      dfm['prod_comp_gap'] = prod_comp_gaps
      dfm['prod_comp_prev'] = prod_comp_prev

    return dfm

# Function to adjust end time for working hours and working days
def adjust_to_working_hours_and_days(start_time, run_time_minutes):
    DAILY_WORK_MINUTES = (WORK_END - WORK_START) * 60  # Convert hours to minutes
    current_time = start_time
    remaining_minutes = run_time_minutes

    while remaining_minutes > 0:
        if current_time.hour < WORK_START or current_time.weekday() in WEEKENDS:
            current_time = next_working_day(current_time.replace(hour=WORK_START, minute=0))
        available_minutes_today = max(
            0, (WORK_END - current_time.hour) * 60 - current_time.minute - 1)
        if remaining_minutes <= available_minutes_today:
            current_time += timedelta(minutes=remaining_minutes)
            remaining_minutes = 0
        else:
            remaining_minutes -= available_minutes_today
            current_time = current_time.replace(hour=WORK_START, minute=0) + timedelta(days=1)
            current_time = next_working_day(current_time)
    return current_time

# Call the function with the dataset
dfm = df.copy()
dfm = schedule_production_with_days(dfm)
dfm = adjust_end_time_and_start_time(dfm)
dfm = dfm.sort_values(by=['Start Time','End Time','Promised Delivery Date'])

dfm.loc[
    (dfm['Process Type'] == 'In House') &
    (dfm['End Time'] > dfm['Promised Delivery Date']), 'Status'] = 'Completed_In House'
dfm.loc[
    (dfm['Process Type'] == 'Outsource') &
    (dfm['End Time'] > dfm['Promised Delivery Date']), 'Status'] = 'Completed_Outsource'
dfm.loc[(dfm['End Time'] < dfm['Promised Delivery Date']), 'Status'] = 'Late'
  
def calculate_business_hours_split(start_time, end_time):
    # Initialize the total business hours
    total_hours = timedelta()

    # Loop through each day between start_time and end_time
    current = start_time
    while current.date() <= end_time.date():
        # Check if the current day is a weekend
        if current.weekday() < 5:  # 0=Monday, ..., 4=Friday
            # Determine the working hours for this day
            day_start = max(current, current.replace(hour=9, minute=0, second=0))
            day_end = min(end_time, current.replace(hour=17, minute=0, second=0))

            # Add the working hours if within working hours range
            if day_start < day_end:
                total_hours += (day_end - day_start)

        # Move to the next day
        current += timedelta(days=1)
        current = current.replace(hour=9, minute=0, second=0)

    # Return the total business hours as a timedelta object
    return total_hours

def calculate_machine_utilization(df):
    # Define working hours (8 hours per day in minutes)
    WORK_HOURS_PER_DAY = 8 * 60

    # Function to calculate daily utilization for a single task
    def calculate_daily_utilization(start, end):
        current = start
        daily_utilization = []

        while current < end:
            # Skip weekends
            if current.weekday() < 5:  # 0 = Monday, ..., 4 = Friday
                # Define work hours for the current day
                work_start = current.replace(hour=9, minute=0, second=0, microsecond=0)
                work_end = current.replace(hour=17, minute=0, second=0, microsecond=0)

                # Adjust the working period for the day to fit within the task's time range
                effective_start = max(current, work_start)
                effective_end = min(end, work_end)

                if effective_start < effective_end:
                    # Calculate minutes of production during this day
                    production_minutes = (effective_end - effective_start).total_seconds() / 60
                    # Store daily utilization (not normalized yet)
                    daily_utilization.append((effective_start.date(), production_minutes))

                current += timedelta(days=1)
            else:
                # Skip to the next day if it's a weekend
                current += timedelta(days=1)

        return daily_utilization

    # Apply the function to calculate daily utilization for each task
    dfm["Daily Utilization"] = dfm.apply(
        lambda row: calculate_daily_utilization(row["Start Time"], row["End Time"]),
        axis=1,
    )

    # Expand the daily utilization into a separate DataFrame
    daily_utilization_expanded = dfm.explode("Daily Utilization").reset_index()

    # Extract the date and production minutes
    daily_utilization_expanded[["Production Date", "Production Minutes"]] = daily_utilization_expanded[
        "Daily Utilization"
    ].apply(pd.Series)

    # Group by machine and date, summing up production minutes for each machine per day
    daily_machine_utilization = daily_utilization_expanded[
        daily_utilization_expanded['Machine Number'] != 'OutSrc'
    ].groupby(["Machine Number", "Production Date"])["Production Minutes"].sum().reset_index()

    # Normalize production minutes by working hours per day
    daily_machine_utilization["Daily Utilization"] = daily_machine_utilization["Production Minutes"] / WORK_HOURS_PER_DAY

    # Group by machine and calculate the average utilization across all days
    average_daily_utilization_per_machine = (
        daily_machine_utilization.groupby("Machine Number")["Daily Utilization"].mean()
    )

    return average_daily_utilization_per_machine

machine_utilization_df = calculate_machine_utilization(dfm.copy())

def calculate_waiting_time(df, group_by_column, date_columns):
    start_col, end_col = date_columns

    # Calculate business hours split for each row
    def business_hours_split(start_time, end_time):
        total_hours = timedelta()
        current = start_time

        while current.date() <= end_time.date():
            if current.weekday() < 5:  # Skip weekends
                day_start = max(current, current.replace(hour=9, minute=0, second=0))
                day_end = min(end_time, current.replace(hour=17, minute=0, second=0))
                if day_start < day_end:
                    total_hours += (day_end - day_start)
            current += timedelta(days=1)
            current = current.replace(hour=9, minute=0, second=0)

        return total_hours

    # Apply the business hours calculation
    dfm['wait_time'] = dfm.apply(
        lambda row: business_hours_split(row[start_col], row[end_col]),
        axis=1
    )

    # Group and calculate the average waiting time
    wait_time_grouped = dfm.groupby(group_by_column)['wait_time'].mean()

    # Format the results
    formatted_results = []
    for group_value, avg_time in wait_time_grouped.items():
        total_seconds = avg_time.total_seconds()
        avg_days = total_seconds // (24 * 3600)
        remaining_seconds = total_seconds % (24 * 3600)
        avg_hours = remaining_seconds // 3600
        avg_decimal_days = total_seconds / (24 * 3600)

        formatted_results.append({
            group_by_column: group_value,
            "Average Days": round(avg_decimal_days, 2),
            "Formatted Time": f"{int(avg_days)} days {int(avg_hours)} hours"
        })

    # Convert to DataFrame for better display
    formatted_df = pd.DataFrame(formatted_results)
    return formatted_df
    
component_waiting_df = calculate_waiting_time(
        dfm,
        group_by_column='Components',
        date_columns=('Order Processing Date', 'Start Time'))
    
    
product_waiting_df = calculate_waiting_time(
        dfm,
        group_by_column='Product Name',
        date_columns=('Order Processing Date', 'Start Time'))

dfm['legend'] = dfm['Components']
for i in range(len(dfm)):
  if dfm['Machine Number'][i] == 'OutSrc':
    dfm['legend'][i] = 'OutSrc'

def late_products(dfm):
    late = dfm.sort_values(by=['Product Name','Components']).groupby('Product Name',as_index=False).last()
    late['late'] = ['late' if late['End Time'][i] > late['Promised Delivery Date'][i] else 'on time' for i in range(len(late))]
    late_df = late.groupby('late')['late'].count()

    return late_df
late_df = late_products(dfm)

def initialise_state():
  if "df" not in st.session_state:
    st.session_state.df = df
  if "dfm" not in st.session_state:  # Adjust Start and End Times
    st.session_state.dfm = dfm
  if "machine_utilization_df" not in st.session_state:
    st.session_state.machine_utilization_df = machine_utilization_df
  if "component_waiting_df" not in st.session_state:
    st.session_state.component_waiting_df = component_waiting_df
  if "product_waiting_df" not in st.session_state:
    st.session_state.product_waiting_df = product_waiting_df
  if "late_df" not in st.session_state:
    st.session_state.late_df = late_df
