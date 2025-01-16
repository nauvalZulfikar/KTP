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

def visualisation(dfm,st):
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
        col1, spacer1, col2, spacer2, col3, spacer3, col4 = st.columns([1, 0.2, 1, 0.2, 1, 0.2, 1])
    
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
                color="legend",  # Use Components for color differentiation
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
                color="legend",  # Use Components for color differentiation
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

    if selected_visualization == "Product Components Status":
        # Initialize session state variables for animation if not already set
        if "auto_refresh" not in st.session_state:
            st.session_state.auto_refresh = False
        if "rows_added" not in st.session_state:
            st.session_state.rows_added = 0
        if "dfm_progress" not in st.session_state:
            st.session_state.dfm_progress = pd.DataFrame(columns=dfm.columns)  # Empty DataFrame for animation
        if "total_rows" not in st.session_state:
            st.session_state.total_rows = len(dfm)  # Total number of rows in the DataFrame
    
        # Start animation button
        if st.button("Start Animation"):
            st.session_state.auto_refresh = True  # Trigger animation
            st.session_state.rows_added = 0  # Reset row counter
            st.session_state.dfm_progress = pd.DataFrame(columns=dfm.columns)  # Reset progress DataFrame
    
        # Clean up the Status column
        dfm['Status'] = dfm['Status'].apply(lambda x: str(x).strip() if x is not None else '')
    
        # Define colors and custom legends for statuses
        status_colors = {
            "InProgress_Outsource": "orange",
            "InProgress_In House": "yellow",
            "Completed_In House": "green",
            "Completed_Outsource": "blue",
            "Late": "red"  # Use a common color for both Late statuses
        }
    
        custom_legend_names = {
            "InProgress_Outsource": "Component Out for Outsource",
            "Completed_Outsource": "Component Back From Outsource and Completed",
            "InProgress_In House": "Component InProgress Inhouse",
            "Completed_In House": "Component Completed Inhouse",
            "Late": "Component Late"  # Use the same legend entry for both Late statuses
        }
    
        fig = go.Figure()
    
        # Progressive animation logic
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
    
        # Display the visualization
        for product in st.session_state.dfm_progress['Product Name'].unique():
            product_data = st.session_state.dfm_progress[st.session_state.dfm_progress['Product Name'] == product]
            for component in product_data['Components'].unique():
                component_data = product_data[product_data['Components'] == component]
                status = component_data['Status'].values[0]
                process_type = component_data['Process Type'].values[0]
                machine_number = component_data['Machine Number'].values[0]
                delay_days = component_data['Delay Days'].fillna(0).values[0]
                delay_hours = component_data['Delay Hours'].fillna(0).values[0]
                start_time = pd.to_datetime(component_data['Start Time'].values[0], errors='coerce')
                end_time = pd.to_datetime(component_data['End Time'].values[0], errors='coerce')
    
                key = f"{status}_{process_type}" if status != "Late" else "Late"
                color = status_colors.get(key, "grey")
    
                hover_text = (
                    f"Product Name: {product}<br>"
                    f"Component: {component}<br>"
                    f"Machine Number: {machine_number}<br>"
                    f"Delay Days: {delay_days}<br>"
                    f"Delay Hours: {delay_hours}<br>"
                    f"Start Time: {start_time.strftime('%d-%b %H:%M') if pd.notnull(start_time) else 'N/A'}<br>"
                    f"End Time: {end_time.strftime('%d-%b %H:%M') if pd.notnull(end_time) else 'N/A'}"
                )
    
                fig.add_trace(go.Scatter(
                    x=[product],
                    y=[component],
                    mode='markers+text',
                    marker=dict(
                        color=color,
                        size=30,
                        symbol='square'
                    ),
                    text=[machine_number],
                    textposition='middle center',
                    name='',
                    legendgroup=key,
                    showlegend=False,
                    hovertemplate=hover_text
                ))
    
        # Add custom legend entries
        for status_key, color in status_colors.items():
            legend_name = custom_legend_names.get(status_key, status_key.replace("_", " and "))
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(
                    color=color,
                    size=10,
                    symbol='square'
                ),
                legendgroup=status_key,
                showlegend=True,
                name=legend_name
            ))
    
        # Update layout
        fig.update_layout(
            title='Animated Status of Each Product Component',
            xaxis_title='Product',
            yaxis_title='Component',
            xaxis=dict(tickmode='array', tickvals=dfm['Product Name'].unique()),
            yaxis=dict(tickmode='array', tickvals=dfm['Components'].unique()),
            legend_title_text='Status and Process Type'
        )
    
        # Display the animated chart
        st.plotly_chart(fig, use_container_width=True)
