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
        st.write(calculate_machine_utilization)
    
    with tabs[1]:
        st.write(component_waiting_df)
    
    with tabs[2]:
        st.write(product_waiting_df)
    
    with tabs[3]:
        st.write(late_products)
    
