import streamlit as st
from scheduler import dfm

def modify():
    # Add Tabs Below
    tabs = st.tabs([
        "In House", 
        "Out Source", 
        "Time Converter"
        ])
    with tabs[0]:
        st.subheader("In House")

    
    with tabs[1]: # Outsource
        products = dfm['Product Name'].unique()
        product_name = [
            products
        ]
        selected_product = st.selectbox(
            'select product name: ',
            product_name
        )

        # product_name = [
        #     'C1',
        #     'C2',
        #     'C3',
        #     'C4',
        #     'C5',
        #     'C6'
        # ]
        # selected_product = st.selectbox(
        #     'select components: ',
        #     selected_product
        # )
        
    with tabs[2]:
        # Radio button for conversion options
        conversion_type = st.radio(
            "Choose a conversion type:",
            ("Days to Minutes", "Hours to Minutes", "Minutes to Days")
        )
        
        # Input field for the user to provide a value
        input_value = st.number_input(
            "Enter the value to convert:", 
            min_value=0.0, 
            step=1.0,
            format="%.2f"
        )
        
        # Perform conversion based on the selected type
        if conversion_type == "Days to Minutes":
            result = input_value * 24 * 60
            st.write(f"{input_value} days is equivalent to {result} minutes.")
        
        elif conversion_type == "Hours to Minutes":
            result = input_value * 60
            st.write(f"{input_value} hours is equivalent to {result} minutes.")
        
        elif conversion_type == "Minutes to Days":
            result = input_value / (24 * 60)
            st.write(f"{input_value} minutes is equivalent to {result:.6f} days.")
