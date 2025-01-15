import streamlit as st

def modify():
    st.subheader("Time Converter")
    
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
