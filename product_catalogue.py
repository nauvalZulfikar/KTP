import pandas as pd
import streamlit as st
from scheduler import dfm, calculate_machine_utilization, component_waiting_df, product_waiting_df, late_products

def product_catalogue():
    df_list = ['Order Processing Date','Promised Delivery Date','Start Time','End Time']

    dfpc = dfm.copy()
    
    for i in df_list:
        dfpc[i] = dfpc[i].dt.strftime('%Y-%m-%d %H:%M')
        
    st.write(dfpc.sort_values(by=['Start Time','End Time']))
    
    # Editable DataFrame
    st.subheader("Edit the DataFrame Below")
    edited_df = st.data_editor(similarity_df, num_rows="dynamic", use_container_width=True)

    # Update the source DataFrame in session state
    st.session_state.similarity_df = edited_df

    st.subheader("Production Scheduling Results")

    # Create two columns
    col1, col2 = st.columns(2)

    # Machine Utilization in the first column
    with col1:
        st.subheader("Machine Utilization")
        machine_utilization_df = calculate_machine_utilization(dfm)
        st.write(machine_utilization_df)

        st.subheader("Component Waiting Time")
        st.write(component_waiting_df)

    # Product Waiting Time and Late Products in the second column
    with col2:
        st.subheader("Late Products")
        late_products_df = late_products(dfm)
        st.write(late_products_df)
        
        st.subheader("Product Waiting Time")
        st.write(product_waiting_df)
