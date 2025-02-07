import pandas as pd
import streamlit as st
import datetime as dt

# initialise_state()

st.write(st.session_state)
def product_catalogue():
    df_list = ['Order Processing Date', 'Promised Delivery Date', 'Start Time', 'End Time']

    # Use a temporary DataFrame for display purposes
    # if 'dfm' in st.session_state:
    display_df = st.session_state.dfm.drop(columns=['Status', 'wait_time', 'legend','Daily Utilization'], errors='ignore')

    # Format date columns in `display_df` only for display
    for col in df_list:
        if col in display_df.columns and pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M')
            
    st.write(display_df.sort_values(by=['Start Time', 'End Time']).reset_index())

    st.subheader("Production Scheduling Results")

    # Define the dataframes and their history to display
    dataframes = {
        "Machine Utilization": ("machine_utilization_df", "machine_utilization_history"),
        "Component Waiting Time": ("component_waiting_df", "component_waiting_history"),
        "Product Waiting Time": ("product_waiting_df", "product_waiting_history"),
        "Late Products": ("late_df", "late_df_history"),
    }

    # Loop through each dataframe and its history
    for title, (current_df_key, history_key) in dataframes.items():
        st.subheader(title)

        # Create columns for the current dataframe and its history
        num_columns = 4  # Maximum number of columns
        columns = st.columns(num_columns)

        # Display the current dataframe in the first column
        if current_df_key in st.session_state:
            with columns[0]:
                st.write("**Current**")
                st.write(st.session_state[current_df_key])

        # Display the history in the remaining columns
        if history_key in st.session_state and st.session_state[history_key]:
            for i, df in enumerate(st.session_state[history_key]):
                if i + 1 < num_columns:  # Ensure we don't exceed the number of columns
                    with columns[i + 1]:
                        st.write(f"**Version {i + 1}**")
                        st.write(df)
                else:
                    break  # Stop if we reach the maximum number of columns
