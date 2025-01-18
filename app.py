import streamlit as st
import pandas as pd
# from scheduler import dfm  # Import the processed `dfm` from the backend
from visualisation import visualisation_tab  # Import Gantt chart visualization
# from results import results
from modify import modify_tab
from product_list_change import product_list_change
from product_catalogue import product_catalogue
from scheduler import df, dfm, product_waiting_df, component_waiting_df, late_df, initialise_state

# Set page configuration
st.set_page_config(
    page_title="Machine Production Scheduler",
    page_icon="🦾",
    layout="wide"
)

# Main Title
st.title("Machine Production Scheduler")

# st.write(st.session_state)

# if "df" not in st.session_state:
#     st.session_state.dfm = df
# if "dfm" not in st.session_state:
#     st.session_state.dfm = dfm
# if "product_waiting_df" not in st.session_state:
#     st.session_state.product_waiting_df = product_waiting_df
# if "component_waiting_df" not in st.session_state:
#     st.session_state.dfm = component_waiting_df
# if "late_df" not in st.session_state:
#     st.session_state.dfm = late_df

# df = st.session_state.df
# dfm = st.session_state.dfm
# product_waiting_df = st.session_state.product_waiting_df
# component_waiting_df =  st.session_state.component_waiting_df 
# late_df = st.session_state.dfm

initialise_state()

# if "late_df" not in st.session_state:
#     st.session_state.late_df = late_df
# if "df" not in st.session_state:
#     st.session_state.df = df
# if "dfm" not in st.session_state:  # Adjust Start and End Times
#     st.session_state.dfm = dfm
# if "component_waiting_df" not in st.session_state:
#     st.session_state.component_waiting_df = component_waiting_df
# if "product_waiting_df" not in st.session_state:
#     st.session_state.product_waiting_df = product_waiting_df

# # File Download Button
# @st.cache_data
# def convert_df_to_excel(df):
#     return df.to_excel(index=False).encode('utf-8')

# csv_file = convert_df_to_excel(dfm)
# st.download_button(
#     label="📥 Download Current File",
#     data=csv_file,
#     file_name="Machine_Production_Schedule.csv",
#     mime="text/csv"
# )

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
