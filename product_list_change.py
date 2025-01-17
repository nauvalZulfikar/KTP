import pandas as pd
import streamlit as st
# from scheduler import dfm 

def product_list_change():
    st.title("Product List Management")

    # Dropdown (Selectbox) for options
    visualization_options = [
        "Add Product",
        "Delete Product",
        "Swap Product",
    ]

    selected_visualization = st.selectbox(
        "Choose an action:",
        visualization_options
    )

    if selected_visualization == "Add Product":
        input1 = st.text_input("Sr. No:")
        input2 = st.text_input("Product Name:")
        input3 = st.date_input("Order Processing Date:")
        input4 = st.date_input("Promised Delivery Date:")
        input5 = st.text_input("Quantity Required:")
        input6 = st.text_input("Components:")
        input7 = st.text_input("Operation:")
        input8 = st.text_input("Process Type:")
        input9 = st.text_input("Machine Number:")
        input10 = st.text_input("Run Time (min/1000):")
        input11 = st.text_input("Cycle Time:")
        input12 = st.text_input("Setup Time (seconds):")

        if st.button("Submit"):
            new_row = pd.DataFrame({
                'Sr. No':input1,
                'Product Name':input2,
                'Order Processing Date':input3,
                'Promised Delivery Date':input4,
                'Quantity Required':input5,
                'Components':input6,
                'Operation':input7,
                'Process Type':input8,
                'Machine Number':input9,
                'Run Time (min/1000)':input10,
                'Cycle Time':input11,
                'Setup Time (seconds)':input12,
            })
            st.session_state.dfm = pd.concat([st.session_state.dfm,pd.DataFrame(new_row)])        
            st.success(f"Product '{input2}' added successfully.")

    elif selected_visualization == "Delete Product":
        input1 = st.number_input("UniqueID:")

        if st.button("Delete"):
            st.session_state.dfm = st.session_state.dfm[st.session_state.dfm['UniqueID']!=input1]
            st.warning(f"Product with ID '{input1}' deleted successfully.")

    elif selected_visualization == "Swap Product":
        input1 = st.number_input("First UniqueID:")
        input2 = st.number_input("Second UniqueID:")

        if st.button("Swap"):
            st.session_state.dfm.loc[st.session_state.dfm['UniqueID']==input1,'UniqueID'] = input2
            st.session_state.dfm.loc[st.session_state.dfm['UniqueID']==input2,'UniqueID'] = input1
            st.info(f"Product '{input1}' swapped with product '{input2}' successfully.")
