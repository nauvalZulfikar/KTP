import pandas as pd
import streamlit as st
from scheduler import dfm

def product_catalogue():
    dfm_list = ['Order Processing Date','Promised Delivery Date','Start Time','End Time']
    
    for i in dfm_list:
        dfm[i] = dfm[i].dt.strftime('%Y-%m-%d %H:%M')
        
    st.write(dfm.sort_values(by=['Start Time','End Time']))
