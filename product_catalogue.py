import pandas as pd
import streamlit as st
from scheduler import dfm

def product_catalogue():
    df_list = ['Order Processing Date','Promised Delivery Date','Start Time','End Time']

    dfpc = dfm.copy()
    
    for i in df_list:
        dfpc[i] = dfpc[i].dt.strftime('%Y-%m-%d %H:%M')
        
    st.write(dfpc.sort_values(by=['Start Time','End Time']))
