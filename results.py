import pandas as pd
import streamlit as st
from scheduler import dfm

def results():
    # Add Tabs Below
    tabs = st.tabs([
        "Product", 
        "Machine Utilisation", 
        "Product Details", 
        "Scheduling Details"
        ])

    with tabs[0]:
        prod_res = dfm.groupby('Product Name').agg(
            total_quantity=pd.NamedAgg(column='Quantity Required', aggfunc='last'),
            average_runtime=pd.NamedAgg(column='Components', aggfunc='nunique'),
            average_duration=pd.NamedAgg(column='Run Time (min/1000)', aggfunc='mean')
        ).reset_index()

        st.write(prod_res)
    
    with tabs[1]:
        mac_res = dfm.groupby('Machine Number').agg(
            total_quantity=pd.NamedAgg(column='Run Time (min/1000)', aggfunc='sum'),
            average_runtime=pd.NamedAgg(column='Components', aggfunc='nunique'),
            average_cycle=pd.NamedAgg(column='Cycle Time (seconds)', aggfunc='mean'),
        ).reset_index()
        
        st.write(mac_res)
    
    with tabs[2]:
        st.write(dfm)
    
    # with tabs[3]:
    #     sched_det = dfm.groupby('Product Name').agg(
    #         total_quantity=pd.NamedAgg(column='Quantity Required', aggfunc='last'),
    #         average_runtime=pd.NamedAgg(column='Components', aggfunc='nunique'),
    #         average_duration=pd.NamedAgg(column='Run Time (min/1000)', aggfunc='mean')
    #     ).reset_index()

    #     st.write(sched_det)
    