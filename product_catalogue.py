import pandas as pd
import streamlit as st
import datetime as dt
from scheduler import calculate_machine_utilization, initialise_state

initialise_state()

st.write(st.session_state)
def product_catalogue():
    df_list = ['Order Processing Date', 'Promised Delivery Date', 'Start Time', 'End Time']

    # Use a temporary DataFrame for display purposes
    if 'dfm' in st.session_state:
        display_df = st.session_state.dfm.drop(columns=['Status', 'wait_time', 'legend','Daily Utilization'], errors='ignore')

        # Format date columns in `display_df` only for display
        for col in df_list:
            if col in display_df.columns and pd.api.types.is_datetime64_any_dtype(display_df[col]):
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M')

        # Display the DataFrame
        st.write(display_df[display_df['Quantity Required']>0].sort_values(by=['Start Time', 'End Time']))

    st.subheader("Production Scheduling Results")

    # Create two columns
    col1, col2 = st.columns(2)

    # Machine Utilization in the first column
    with col1:
        st.subheader("Machine Utilization")
        if "machine_utilization_df" in st.session_state:
            st.write(st.session_state.machine_utilization_df)

        st.subheader("Component Waiting Time")
        # if "component_waiting_df" not in st.session_state:
        #     st.session_state.component_waiting_df = component_waiting_df
        if "component_waiting_df" in st.session_state:
            st.write(st.session_state.component_waiting_df)

    # Product Waiting Time and Late Products in the second column
    with col2:
        st.subheader("Late Products")
        # if "late_products_df" not in st.session_state:
        #     st.session_state.late_products_df = late_products(st.session_state.dfm)
        if "late_products_df" in st.session_state:    
            st.write(st.session_state.late_products_df)

        st.subheader("Product Waiting Time")
        # if "product_waiting_df" not in st.session_state:
        #     st.session_state.product_waiting_df = product_waiting_df
        if "product_waiting_df" in st.session_state:
            st.write(st.session_state.product_waiting_df)
