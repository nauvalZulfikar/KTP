import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_autorefresh import st_autorefresh  # Import st_autorefresh

# Set page configuration
st.set_page_config(
    page_title="Machine Production Scheduler",
    page_icon="✨",
    layout="wide"
)

# Main Title
st.title("Machine Production Scheduler")

# Add Tabs Below
tabs = st.tabs(["Visualisation", "Product List Change", "Product Catalogue", "Similarity Catalogue", "Modify", "Results", "Instructions"])

# Initialize session state variables for Gantt chart
if "gantt_data" not in st.session_state:
    st.session_state.gantt_data = pd.DataFrame(columns=["Task", "Start", "End", "Category", "Department"])
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False  # Auto-refresh toggle
if "row_limit" not in st.session_state:
    st.session_state.row_limit = 5  # Number of tasks to add
if "rows_added" not in st.session_state:
    st.session_state.rows_added = 0  # Counter for tasks added

# Tab Content
with tabs[0]:  # Visualisation Tab
    st.subheader("Visualisation")

    # Dropdown (Selectbox) for visualization options
    visualization_options = [
        "Progressive Gantt Chart",
        "Gantt Chart (Unschedule)",
        "Machine Utilisation",
        "Time Taken by Each Machine",
        "Time Taken by Each Product",
        "Wait Time",
        "Idle Time",
        "Product Components Status",
        "Remaining Time"
    ]

    selected_visualization = st.selectbox(
        "Choose a visualization:",
        visualization_options
    )

    if selected_visualization == "Progressive Gantt Chart":
        st.write("Progressively plotting a Gantt chart.")

        # Start button to trigger or reset the Gantt chart
        if st.button("Start Progressive Gantt Chart"):
            # Reset the data and counters
            st.session_state.gantt_data = pd.DataFrame(columns=["Task", "Start", "End", "Category", "Department"])
            st.session_state.rows_added = 0
            st.session_state.auto_refresh = True

        # Auto-refresh logic
        if st.session_state.auto_refresh and st.session_state.rows_added < st.session_state.row_limit:
            st_autorefresh(interval=1000, limit=None, key="autorefresh")  # Refresh every second
            # Add a new task with progressive Task ID and random start/end times
            task_id = f"Task {st.session_state.rows_added + 1}"
            start_time = pd.Timestamp.now() + pd.to_timedelta(np.random.randint(0, 5), unit="h")
            end_time = start_time + pd.to_timedelta(np.random.randint(1, 5), unit="h")
            category = np.random.choice(["Critical", "Important", "Normal"])
            department = np.random.choice(["HR", "IT", "Finance"])
            new_row = {"Task": task_id, "Start": start_time, "End": end_time, "Category": category, "Department": department}
            st.session_state.gantt_data = pd.concat([st.session_state.gantt_data, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.rows_added += 1

        # Stop auto-refresh automatically when all tasks are added
        if st.session_state.rows_added >= st.session_state.row_limit:
            st.session_state.auto_refresh = False
            st.success("Progressive Gantt Chart completed! Click the button to restart.")

        # Display the Gantt chart using Plotly
        if not st.session_state.gantt_data.empty:
            fig = px.timeline(
                st.session_state.gantt_data,
                x_start="Start",
                x_end="End",
                y="Task",
                color="Category",
                hover_name="Task",
                title="Progressive Multi-Variable Gantt Chart",
                labels={"Category": "Task Category"}
            )
            fig.update_yaxes(categoryorder="total ascending")  # Sort tasks
            fig.update_layout(
                legend_title="Task Categories",
                xaxis_title="Time",
                yaxis_title="Tasks"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Click the button to start plotting the Gantt chart.")

    elif selected_visualization == "Machine Utilisation":
        st.write("Displaying Machine Utilisation...")
        st.bar_chart(np.random.randint(1, 100, size=(5, 3)))

    else:
        st.write(f"Visualization for {selected_visualization} is not yet implemented.")

with tabs[1]:
    st.subheader("Product List Change")
    st.write("This tab is for managing product list changes.")

with tabs[2]:
    st.subheader("Product Catalogue")
    st.write("This tab is for managing the product catalogue.")

with tabs[3]:
    st.subheader("Similarity Catalogue")
    st.write("This tab is for managing the similarity catalogue.")

with tabs[4]:
    st.subheader("Modify")
    st.write("This tab is for making modifications.")

with tabs[5]:
    st.subheader("Results")
    st.write("This tab displays the results of the analyses.")

with tabs[6]:
    st.subheader("Instructions")
    st.write("This tab contains instructions for using the app.")

# Footer
st.markdown("---")
st.markdown("👨‍💻 Developed with Nauval Zulfikar.")
