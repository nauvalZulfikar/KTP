import pandas as pd
import streamlit as st
import datetime as dt

# initialise_state()

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

    # Display current dataframes
    st.subheader("Machine Utilization")
    if "machine_utilization_df" in st.session_state:
        st.write(st.session_state.machine_utilization_df)

    st.subheader("Component Waiting Time")
    if "component_waiting_df" in st.session_state:
        st.write(st.session_state.component_waiting_df)

    st.subheader("Product Waiting Time")
    if "product_waiting_df" in st.session_state:
        st.write(st.session_state.product_waiting_df)

    st.subheader("Late Products")
    if "late_df" in st.session_state:
        st.write(st.session_state.late_df)

    # Display history dataframes
    st.subheader("History of DataFrames")

    # Display dataframe_history
    if "dataframe_history" in st.session_state and st.session_state.dataframe_history:
        with st.expander("DataFrame History"):
            for i, df in enumerate(st.session_state.dataframe_history):
                st.write(f"DataFrame Version {i + 1}")
                st.write(df)

    # Display machine_utilization_history
    if "machine_utilization_history" in st.session_state and st.session_state.machine_utilization_history:
        with st.expander("Machine Utilization History"):
            for i, df in enumerate(st.session_state.machine_utilization_history):
                st.write(f"Machine Utilization Version {i + 1}")
                st.write(df)

    # Display component_waiting_history
    if "component_waiting_history" in st.session_state and st.session_state.component_waiting_history:
        with st.expander("Component Waiting Time History"):
            for i, df in enumerate(st.session_state.component_waiting_history):
                st.write(f"Component Waiting Time Version {i + 1}")
                st.write(df)

    # Display product_waiting_history
    if "product_waiting_history" in st.session_state and st.session_state.product_waiting_history:
        with st.expander("Product Waiting Time History"):
            for i, df in enumerate(st.session_state.product_waiting_history):
                st.write(f"Product Waiting Time Version {i + 1}")
                st.write(df)

    # Display late_df_history
    if "late_df_history" in st.session_state and st.session_state.late_df_history:
        with st.expander("Late Products History"):
            for i, df in enumerate(st.session_state.late_df_history):
                st.write(f"Late Products Version {i + 1}")
                st.write(df)
