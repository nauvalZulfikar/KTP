import streamlit as st
from scheduler import dfm

dfn = dfm.drop(columns=['wait_time','legend','Status']).copy()

def modify():
    # Add Tabs Below
    tabs = st.tabs([
        "In House", 
        "Out Source", 
        "Time Converter"
        ])
    with tabs[0]:
        st.subheader("In House")

    
    with tabs[1]:  # Outsource
        products = dfn['Product Name'].unique()  # Get unique product names
        selected_product = st.selectbox(
            'Select product name:',
            products  # Pass the array directly without wrapping it in a list
        )

        components = dfn[dfn['Product Name']==selected_product]['Components'].unique()
        selected_components = st.selectbox(
            'select components: ',
            components
        )

        field = dfn.columns
        selected_fields = st.selectbox(
            'select fields: ',
            field
        )

        int_col = ['UniqueID','Sr. No','Quantity Required','Run Time (min/1000)','Cycle Time (seconds)','Setup time (seconds)']
        str_col = ['Product Name','Components','Operation','Process Type','Machine Number']
        date_col = ['Order Processing Date','Promised Delivery Date']

        if selected_fields in int_col:
            edit_input = st.number_input(
                'Enter new value: '
            )
        elif selected_fields in str_col:
            edit_input = st.text_input(
                'Enter new value: '
            )
        else:
            edit_input = st.date_input(
                'Enter new value: '
            )
            
        if st.button('Confirm'):
            dfn.loc[
             (dfn['Product Name']==selected_product)&
             (dfn['Components']==selected_components),
             selected_fields
             ] = edit_input
        
        st.dataframe(dfn[
                     (dfn['Product Name']==selected_product)&
                     (dfn['Components']==selected_components)
                     ])
        
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
