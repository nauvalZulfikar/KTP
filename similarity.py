import pandas as pd
import streamlit as st

def similarity():
    # Editable DataFrame
    st.subheader("Edit the DataFrame Below")
    edited_df = st.data_editor(similarity_df, num_rows="dynamic", use_container_width=True)

    # Update the source DataFrame in session state
    st.session_state.similarity_df = edited_df
