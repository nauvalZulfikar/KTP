import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import streamlit as st
from scheduler import dfm, adjust_to_working_hours_and_days, calculate_machine_utilization, product_waiting_df, component_waiting_df

# Create Bar Charts
def create_bar_chart(data, x_col, y_col, color=None):
    fig = px.bar(
        data,
        x=x_col,
        y=y_col,
        color=color,
        text=y_col,
        labels={x_col: "Category", y_col: "Average Days"},
    )
    fig.update_traces(texttemplate="%{text:.2f} days", textposition="outside")
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Average Waiting Time (Days)",
        template="plotly_white",
        showlegend=bool(color),
    )
    return fig

def visualisation(df,st):
    st.subheader("Visualisation")

    # Initialize session state for progressive visualization
    if "dfm_progress" not in st.session_state:
        st.session_state.dfm_progress = dfm.copy()  # Initially show the full DataFrame
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False  # Auto-refresh toggle
    if "rows_added" not in st.session_state:
        st.session_state.rows_added = len(dfm)  # Start with all rows added
    if "total_rows" not in st.session_state:
        st.session_state.total_rows = len(dfm)  # Total rows in the DataFrame

    # Layout for buttons with reduced spacing
    with st.container():
        col1, col2, col3, col4,  spacer = st.columns([1, 1, 1, 1, 2.5])
    
        with col1:
            if st.button("Start"):
                # Reset the progress DataFrame and counters for animation
                st.session_state.dfm_progress = pd.DataFrame(columns=dfm.columns)
                st.session_state.rows_added = 0
                st.session_state.auto_refresh = True
        with col2:
            if st.button("Pause"):
                # Pause the auto-refresh
                st.session_state.auto_refresh = False
                st.info("Animation paused.")
        with col3:
            if st.button("Reschedule"):
                # Reschedule logic - reset the progress to start fresh
                st.session_state.dfm_progress = pd.DataFrame(columns=dfm.columns)
                st.session_state.rows_added = 0
                st.info("Rescheduling initiated. Click 'Start' to animate again.")
        with col4:
            if st.button("Reset"):
                # Reset all session state variables
                st.session_state.dfm_progress = pd.DataFrame(columns=dfm.columns)
                st.session_state.rows_added = 0
                st.session_state.auto_refresh = False
                st.success("Progress reset successfully.")

    # Dropdown (Selectbox) for visualization options
    visualization_options = [
        "Gantt Chart",
        "Gantt Chart (Unscheduled)",
        "Machine Utilisation",
        "Product Waiting Time",
        "Component Waiting Time",
        "Product Components Status"
    ]

    selected_visualization = st.selectbox(
        "Choose a visualization:",
        visualization_options
    )

    if selected_visualization == "Gantt Chart":
        # Static Gantt chart displayed immediately when the page loads
        if not st.session_state.auto_refresh:  # Show the static chart if not animating
            fig_static = px.timeline(
                st.session_state.dfm_progress,
                x_start="Start Time",
                x_end="End Time",
                y="Product Name",
                color="mac_comp",  # Use Components for color differentiation
                # labels={"Components": "Component", "Machine Number": "Machine"}
            )
            fig_static.update_yaxes(categoryorder="total ascending")  # Sort tasks
            fig_static.update_layout(
                legend_title="Component",
                xaxis_title="Time",
                yaxis_title="Products"
            )
            st.plotly_chart(fig_static, use_container_width=True)

        # Progressive animation
        if st.session_state.auto_refresh and st.session_state.rows_added < st.session_state.total_rows:
            st_autorefresh(interval=1000, limit=None, key="autorefresh")  # Refresh every second
            # Add the next row to the progress DataFrame
            st.session_state.dfm_progress = pd.concat(
                [st.session_state.dfm_progress, dfm.iloc[st.session_state.rows_added:st.session_state.rows_added + 1]],
                ignore_index=True
            )
            st.session_state.rows_added += 1  # Increment the counter

        # Stop animation when all rows are added
        if st.session_state.rows_added >= st.session_state.total_rows:
            st.session_state.auto_refresh = False
            st.success("Animation complete! Reload the page to reset.")

        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            fig_animated = px.timeline(
                st.session_state.dfm_progress,
                x_start="Start Time",
                x_end="End Time",
                y="Product Name",
                color="Components",  # Use Components for color differentiation
                labels={"Components": "Component", "Machine Number": "Machine"}
            )
            fig_animated.update_yaxes(categoryorder="total ascending")  # Sort tasks
            fig_animated.update_layout(
                legend_title="Component",
                xaxis_title="Time",
                yaxis_title="Products"
            )
            st.plotly_chart(fig_animated, use_container_width=True)

    elif selected_visualization == "Gantt Chart (Unscheduled)":
        # Step 1: Calculate durations
        data = dfm.copy()  # Ensure the original DataFrame is not modified
        data['Duration'] = data['Quantity Required'] / 1000 * data['Run Time (min/1000)']

        # Step 2: Adjust durations for working hours and days
        data['Adjusted End Time'] = data.apply(
            lambda row: adjust_to_working_hours_and_days(row['Order Processing Date'], row['Duration']),
            axis=1
        )

        # Step 3: Create a horizontal bar chart
        fig = px.bar(
            data,
            x="Duration",  # Horizontal axis
            y="Product Name",  # Vertical axis
            color="Components",  # Color by components
            orientation="h",  # Horizontal bars
            labels={"Duration": "Task Duration (minutes)", "Product Name": "Product", "Components": "Component"},
            # title="Horizontal Bar Chart of Task Durations"
        )

        fig.update_layout(
            xaxis_title="Task Duration (minutes)",
            yaxis_title="Products",
            legend_title="Components",
            template="plotly_white"
        )

        # Step 4: Integrate into Streamlit
        # st.title("Horizontal Bar Chart Visualization")
        st.plotly_chart(fig, use_container_width=True)

    elif selected_visualization == "Machine Utilisation":
        # Calculate machine utilization
        average_utilization = calculate_machine_utilization(dfm)

        # Prepare data for visualization
        utilization_df = average_utilization.reset_index()
        utilization_df.columns = ["Machine Number", "Average Utilization"]
        utilization_df["Average Utilization (%)"] = utilization_df["Average Utilization"] * 100

        # Create a bar chart
        fig = px.bar(
            utilization_df,
            x="Machine Number",
            y="Average Utilization (%)",
            text="Average Utilization (%)",
            labels={"Average Utilization (%)": "Utilization (%)", "Machine Number": "Machine"},
            # title="Average Daily Machine Utilization",
            color="Machine Number",
        )

        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            xaxis_title="Machine",
            yaxis_title="Utilization (%)",
            template="plotly_white",
            showlegend=False,
        )

        # Integrate into Streamlit
        # st.title("Machine Utilization Visualization")
        st.plotly_chart(fig, use_container_width=True)

    elif selected_visualization == "Product Waiting Time":
        component_chart = create_bar_chart(
            component_waiting_df, 
            x_col="Components", 
            y_col="Average Days", 
        )

        # st.subheader("Average Waiting Time by Component")
        st.plotly_chart(component_chart, use_container_width=True)

    elif selected_visualization == "Component Waiting Time":
        product_chart = create_bar_chart(
            product_waiting_df, 
            x_col="Product Name", 
            y_col="Average Days", 
        )

        # st.subheader("Average Waiting Time by Product")
        st.plotly_chart(product_chart, use_container_width=True)

    # elif selected_visualization == "Product Components Status":
    #     prod_comp_stat(dfm, st)
