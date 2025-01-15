import pandas as pd
import streamlit as st
from scheduler import calculate_machine_utilization, component_waiting_df, product_waiting_df, late_products

def results():
    # Add Tabs Below
    tabs = st.tabs([
        "Machine Utilisation", 
        "Product Waiting Time", 
        "Component Waiting time", 
        "Late Products"
        ])

    with tabs[0]:
        # prod_res = dfm.groupby('Product Name').agg(
        #     total_quantity=pd.NamedAgg(column='Quantity Required', aggfunc='last'),
        #     average_runtime=pd.NamedAgg(column='Components', aggfunc='nunique'),
        #     average_duration=pd.NamedAgg(column='Run Time (min/1000)', aggfunc='mean')
        # ).reset_index()

        # st.write(prod_res)
        st.write(calculate_machine_utilization)
    
    with tabs[1]:
        # mac_res = dfm.groupby('Machine Number').agg(
        #     total_quantity=pd.NamedAgg(column='Run Time (min/1000)', aggfunc='sum'),
        #     average_runtime=pd.NamedAgg(column='Components', aggfunc='nunique'),
        #     average_cycle=pd.NamedAgg(column='Cycle Time (seconds)', aggfunc='mean'),
        # ).reset_index()
        
        # st.write(mac_res)
        st.write(component_waiting_df)
    
    with tabs[2]:
        st.write(product_waiting_df)
    
    with tabs[3]:
        st.write(late_products)
    
