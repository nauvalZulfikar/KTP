import pandas as pd
import streamlit as st

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
        st.subheader("Add New Product")
        input1 = st.text_input("Sr. No:")
        input2 = st.text_input("Product Name:")
        input3 = st.date_input("Order Processing Date:")
        input4 = st.date_input("Promised Delivery Date:")
        input5 = st.text_input("Quantity Required:")
        input6 = st.text_input("Components:")
        input1 = st.text_input("Operation:")
        input2 = st.text_input("Process Type:")
        input3 = st.text_input("Machine Number:")
        input4 = st.text_input("Run Time (min/1000):")
        input5 = st.text_input("Cycle Time:")
        input6 = st.text_input("Setup Time (seconds):")

        if st.button("Add Product"):
            st.success(f"Product '{input2}' added successfully.")

    elif selected_visualization == "Delete Product":
        st.subheader("Delete Product")
        input1 = st.text_input("UniqueID:")

        if st.button("Delete Product"):
            st.warning(f"Product with ID '{input1}' deleted successfully.")

    elif selected_visualization == "Swap Product":
        st.subheader("Swap Product")
        input1 = st.text_input("First UniqueID:")
        input2 = st.text_input("SecondID:")

        if st.button("Swap Products"):
            st.info(f"Product '{input1}' swapped with product '{input2}' successfully.")