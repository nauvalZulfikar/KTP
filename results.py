import pandas as pd
import streamlit as st
from scheduler import dfm, calculate_machine_utilization, component_waiting_df, product_waiting_df, late_products

def results():
    st.title("Production Scheduling Results")

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
