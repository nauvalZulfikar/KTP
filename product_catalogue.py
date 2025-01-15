import pandas as pd
import streamlit as st
from scheduler import dfm

def product_catalogue():
    st.write(dfm.sort_values(by=['Start Time','End Time']))