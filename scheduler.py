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

def extract_machine_state(animated_data):
    machine_schedule = defaultdict(list)
    machine_last_end = {}

    for machine in animated_data['Machine Number'].unique():
        # Get all rows for this machine
        machine_rows = animated_data[animated_data['Machine Number'] == machine]
        # Sort by Start Time to ensure proper scheduling order
        machine_rows = machine_rows.sort_values(by='Start Time')

        # Update the machine_schedule and machine_last_end
        for _, row in machine_rows.iterrows():
            machine_schedule[machine].append((row['Start Time'], row['End Time'], row.name))
        machine_last_end[machine] = machine_rows['End Time'].max()

    return machine_schedule, machine_last_end

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

        # Go through each task, one by one
        i = 0
        while i < len(data):  # Use a while loop to dynamically handle new rows
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
                i += 1  # Move to the next task
                continue

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
                producible_qty = (available_minutes / run_time_minutes) * data['Quantity Required'][i]

                # Update the task with the producible quantity
                data.at[i, 'Quantity Required'] = int(producible_qty)

                # If there’s remaining work, create a new task for it
                if producible_qty > 0:
                    remaining_qty = data['Quantity Required'][i] - producible_qty
                    remaining_task = data.iloc[i].copy()
                    remaining_task['Quantity Required'] = remaining_qty
                    remaining_task['Start Time'] = None
                    remaining_task['End Time'] = None
                    data.loc[len(data)] = remaining_task  # Add the new task to the dataset

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

            i += 1  # Move to the next task

        # Check if any tasks are still unscheduled
        has_empty_rows = data['Start Time'].isna().any() or data['End Time'].isna().any()

    data['Quantity Required'] = data['Quantity Required'].apply(lambda x: round(x))

    # Return the completed schedule
    return data

def reschedule_production_with_days(data, machine_last_end, machine_schedule, previous_schedule):
    # We start by assuming there are tasks that need to be scheduled
    has_empty_rows = True
    # Keep trying to schedule tasks until all tasks have a Start and End Time
    while has_empty_rows:
        # Go through each task, one by one
        i = 0
        while i < len(data):  # Use a while loop to dynamically handle new rows
            # Skip tasks that already have a start and end time
            if not pd.isna(data.at[i, 'Start Time']) and not pd.isna(data.at[i, 'End Time']):
                i += 1
                continue

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
            if machine == "OutSrc":
                # Look for the previous component's end time for the same product
                prev_component_end_time = data.iloc[:i][
                    (data.iloc[:i]['Product Name'] == product) &
                    (data.iloc[:i]['Components'] < component)
                ]['End Time'].max()

                # Use product's last end time if no previous component exists
                if pd.isna(prev_component_end_time):
                    prev_component_end_time = data['Order Processing Date'][i].replace(hour=WORK_START, minute=0)

                # Start this task after the previous component ends
                start_time = prev_component_end_time
                # Calculate how long the task will take
                run_time_minutes = data['Run Time (min/1000)'][i] * data['Quantity Required'][i] / 1000
                # Determine when the task will end
                end_time = adjust_to_working_hours_and_days(start_time, run_time_minutes)

                # Save the Start and End Times for this task
                data.at[i, 'Start Time'] = start_time
                data.at[i, 'End Time'] = end_time
                i += 1  # Move to the next task
                continue

            # ==========================
            # MACHINE SCHEDULING
            # ==========================
            # Look for earlier tasks for the same product in the current dataset
            same_product_prev = data.iloc[:i][data.iloc[:i]['Product Name'] == product]
            if not same_product_prev.empty:
                # If there are earlier tasks in the current dataset, use the last task's end time
                product_last_end = same_product_prev.iloc[-1]['End Time']
            else:
                # Otherwise, check the previous schedule for earlier tasks
                previous_product_prev = previous_schedule[
                    (previous_schedule['Product Name'] == product) &
                    (previous_schedule['Components'] < component)
                ]
                if not previous_product_prev.empty:
                    # Use the end time of the last scheduled task in the previous schedule
                    product_last_end = previous_product_prev['End Time'].max()
                else:
                    # If no previous tasks exist, start after the order processing date
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
                producible_qty = (available_minutes / run_time_minutes) * data['Quantity Required'][i]

                # Update the task with the producible quantity
                data.at[i, 'Quantity Required'] = int(producible_qty)

                # If there’s remaining work, create a new task for it
                if producible_qty > 0:
                    remaining_qty = data['Quantity Required'][i] - producible_qty
                    remaining_task = data.iloc[i].copy()
                    remaining_task['Quantity Required'] = remaining_qty
                    remaining_task['Start Time'] = None
                    remaining_task['End Time'] = None

                    # Append the new task to the DataFrame
                    next_index = data.index[-1] + 1  # Determine the next available index
                    data.loc[next_index] = remaining_task  # Add the new task

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

            i += 1  # Move to the next task

        # Check if any tasks are still unscheduled
        has_empty_rows = data['Start Time'].isna().any() or data['End Time'].isna().any()

    data['Quantity Required'] = data['Quantity Required'].apply(lambda x: round(x))

    # Return the completed schedule
    return data

def calculate_gaps(df):
    loop_len = max(df['Product Name'].value_counts())
    df = df.groupby('Product Name', as_index=False).first().sort_values(by=['Promised Delivery Date', 'Start Time','End Time']).reset_index(drop=True)

    for x in range(1,loop_len+1):
      dfj = df.groupby('Product Name', as_index=False).nth(x).sort_values(by=['Promised Delivery Date', 'Start Time','End Time']).reset_index(drop=True)
      df = pd.concat([df, dfj]).sort_values(by=['Promised Delivery Date', 'Start Time']).reset_index(drop=True)

      # Calculate gaps based on machine usage
      df = df.sort_values(by=['Machine Number','Start Time','End Time']).reset_index(drop=True)
      machine_gaps = [0]
      machine_prev = [0]
      for i in range(len(df) - 1):
          if df['Machine Number'].iloc[i] == df['Machine Number'].iloc[i + 1]:
              gap = (df['Start Time'].iloc[i + 1] - df['End Time'].iloc[i]).total_seconds() / 60  # Minutes
              prev_m = df['UniqueID'][i]
          else:
              gap = 0
              prev_m = 0
          if df['Machine Number'].iloc[i] == 'OutSrc':
              gap = 0
          machine_gaps.append(gap)
          machine_prev.append(prev_m)
      df['machine_gaps'] = machine_gaps
      df['machine_prev'] = machine_prev

      # Calculate gaps based on product name and components
      df = df.sort_values(by=['Start Time','End Time','Product Name','Components',]).reset_index(drop=True)
      prod_comp_gaps = [0]
      prod_comp_prev = [0]
      for i in range(len(df) - 1):
          if df['Product Name'].iloc[i] == df['Product Name'].iloc[i + 1] and df['Components'].iloc[i] != df['Components'].iloc[i + 1]:
              gap = (df['Start Time'].iloc[i + 1] - df['End Time'].iloc[i]).total_seconds() / 60  # Minutes
              prev_pc = df['UniqueID'][i]
          else:
              gap = 0
              prev_pc = 0
          prod_comp_gaps.append(gap)
          prod_comp_prev.append(prev_pc)
      df['prod_comp_gap'] = prod_comp_gaps
      df['prod_comp_prev'] = prod_comp_prev

    return df

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
    df["Daily Utilization"] = df.apply(
        lambda row: calculate_daily_utilization(row["Start Time"], row["End Time"]),
        axis=1,
    )

    # Expand the daily utilization into a separate DataFrame
    daily_utilization_expanded = df.explode("Daily Utilization").reset_index()

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
    df['wait_time'] = df.apply(
        lambda row: business_hours_split(row[start_col], row[end_col]),
        axis=1
    )

    # Group and calculate the average waiting time
    wait_time_grouped = df.groupby(group_by_column)['wait_time'].mean()

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
  
def late_products(df):
    late = df.sort_values(by=['Product Name','Components']).groupby('Product Name',as_index=False).last()
    late['late'] = ['late' if late['End Time'][i] > late['Promised Delivery Date'][i] else 'on time' for i in range(len(late))]
    late_df = late.groupby('late')['late'].count().reset_index(name='count')

    return late_df
