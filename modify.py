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

    int_col = ['UniqueID','Sr. No','Quantity Required','Run Time (min/1000)','Cycle Time (seconds)','Setup time (seconds)']
    str_col = ['Product Name','Components','Operation','Process Type','Machine Number']
    date_col = ['Order Processing Date','Promised Delivery Date']

    with tabs[0]: # In House
        df_in = dfn[dfn['Process Type']=='In House']
        in_products = df_in['Product Name'].unique()  # Get unique product names
        in_selected_product = st.selectbox(
            'Select product name:',
            in_products  # Pass the array directly without wrapping it in a list
        )

        in_components = df_in[df_in['Product Name']==in_selected_product]['Components'].unique()
        in_selected_components = st.selectbox(
            'select components: ',
            in_components
        )

        in_field = df_in.columns
        in_selected_fields = st.selectbox(
            'select fields: ',
            in_field
        )

        if in_selected_fields in int_col:
            in_edit_input = st.number_input(
                'Enter new value: '
            )
        elif in_selected_fields in str_col:
            in_edit_input = st.text_input(
                'Enter new value: '
            )
        else:
            in_edit_input = st.date_input(
                'Enter new value: '
            )
            
        if st.button('Confirm'):
            df_in.loc[
             (df_in['Product Name']==in_selected_product)&
             (df_in['Components']==in_selected_components),
             in_selected_fields
             ] = in_edit_input
        
        st.dataframe(df_in[
                     (df_in['Product Name']==in_selected_product)&
                     (df_in['Components']==in_selected_components)
                     ])

    
    with tabs[1]:  # Outsource
        df_out = dfn[dfn['Process Type']=='Outsource']
        out_products = df_out['Product Name'].unique()  # Get unique product names
        out_selected_product = st.selectbox(
            'Select product name:',
            out_products  # Pass the array directly without wrapping it in a list
        )

        out_components = df_out[df_out['Product Name']==out_selected_product]['Components'].unique()
        out_selected_components = st.selectbox(
            'select components: ',
            components
        )

        out_field = df_out.columns
        out_selected_fields = st.selectbox(
            'select fields: ',
            out_field
        )
        
        if out_selected_fields in int_col:
            out_edit_input = st.number_input(
                'Enter new value: '
            )
        elif out_selected_fields in str_col:
            out_edit_input = st.text_input(
                'Enter new value: '
            )
        else:
            out_edit_input = st.date_input(
                'Enter new value: '
            )
            
        if st.button('Confirm'):
            df_out.loc[
             (df_out['Product Name']==out_selected_product)&
             (df_out['Components']==out_selected_components),
             out_selected_fields
             ] = out_edit_input
        
        st.dataframe(df_out[
                     (df_out['Product Name']==out_selected_product)&
                     (df_out['Components']==out_selected_components)
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
