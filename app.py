import streamlit as st
# from streamlit_gsheets import GSheetsConnection
st.set_page_config(
    page_title="Machine Production Scheduler",
    page_icon="🦾",
    layout="wide"
)

import pandas as pd
from visualisation import visualisation_tab  # Import Gantt chart visualization
from modify import modify_tab
from product_list_change import product_list_change
from product_catalogue import product_catalogue
from scheduler import late_products, calculate_waiting_time, calculate_machine_utilization, adjust_end_time_and_start_time, schedule_production_with_days


# gspread_link = 'https://docs.google.com/spreadsheets/d/1rg9IsiTwd9dGGOww29eHJF_4gkp6gK4B/edit?usp=sharing&ouid=116867237747845550170&rtpof=true&sd=true'
# Set page configuration


# Main Title
st.title("Machine Production Scheduler")

# st.write(st.session_state)

# df, dfm, component_waiting_df, product_waiting_df, late_df
df = pd.read_excel('Product Details_v1.xlsx', sheet_name='P')
df['Order Processing Date'] = pd.to_datetime(df['Order Processing Date'])
df['Promised Delivery Date'] = pd.to_datetime(df['Promised Delivery Date'])
df['Start Time'] = pd.NaT  # Initialize as empty datetime
df['End Time'] = pd.NaT  # Initialize as empty datetime
df['status'] = ''  # Initialize the Status column
df.loc[df['Process Type'] == 'In House', 'status'] = 'InProgress_In House'
df.loc[df['Process Type'] == 'Outsource','status'] = 'InProgress_Outsource'
df = df.sort_values(by=['Promised Delivery Date',
                        'Product Name',
                        'Components']).reset_index(drop=True)

dfm = df.copy()
dfm = schedule_production_with_days(dfm)
dfm = adjust_end_time_and_start_time(dfm)
dfm = dfm.sort_values(by=['Start Time','End Time','Promised Delivery Date'])
# dfm.loc[
#     (dfm['Process Type'] == 'In House') &
#     (dfm['End Time'] > dfm['Promised Delivery Date']), 'Status'] = 'Completed_In House'
# dfm.loc[
#     (dfm['Process Type'] == 'Outsource') &
#     (dfm['End Time'] > dfm['Promised Delivery Date']), 'Status'] = 'Completed_Outsource'
# dfm.loc[(dfm['End Time'] < dfm['Promised Delivery Date']), 'Status'] = 'Late'
dfm['legend'] = dfm['Components']
for i in range(len(dfm)):
  if dfm['Machine Number'][i] == 'OutSrc':
    dfm['legend'][i] = 'OutSrc'

machine_utilization_df = calculate_machine_utilization(dfm.copy())

component_waiting_df = calculate_waiting_time(
        dfm,
        group_by_column='Components',
        date_columns=('Order Processing Date', 'Start Time'))

product_waiting_df = calculate_waiting_time(
        dfm,
        group_by_column='Product Name',
        date_columns=('Order Processing Date', 'Start Time'))

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

initialise_state()

# Add Tabs Below
tabs = st.tabs([
    "Visualisation",  
    "Modify",
    "Product List Change", 
    "Product Catalogue", 
    # "Similarity Catalogue", 
    # "Results",
    ])

# Tab Content
with tabs[0]:  # Visualisation Tab
    # if "dfm" in st.session_state:
        # dfm = st.session_state.dfm
    visualisation_tab()

    
with tabs[1]:
    modify_tab()

with tabs[2]:
    product_list_change()

with tabs[3]:
    product_catalogue()

# with tabs[4]:
#     similarity()

# with tabs[5]:
#     results()


# if "late_df" not in st.session_state:
st.session_state.late_df = late_df
# if "df" not in st.session_state:
st.session_state.df = df
# if "dfm" not in st.session_state:  # Adjust Start and End Times
st.session_state.dfm = dfm
# if "component_waiting_df" not in st.session_state:
st.session_state.component_waiting_df = component_waiting_df
# if "product_waiting_df" not in st.session_state:
st.session_state.product_waiting_df = product_waiting_df
