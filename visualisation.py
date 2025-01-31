import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import streamlit as st
from collections import defaultdict
from scheduler import adjust_to_working_hours_and_days, calculate_machine_utilization, adjust_end_time_and_start_time, schedule_production_with_days, reschedule_production_with_days, calculate_waiting_time, late_products
import time

# Inject CSS to frame all visualizations
st.markdown("""
    <style>
        div.stPlotlyChart {
            border: 2px solid white !important;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

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

def visualisation_tab():
    # Add custom CSS for white borders
    # add_custom_css()
    
    st.subheader("Visualisation")

    # Constants
    WORK_START = 9

    # Initialize session state for progressive visualization
    if "dfm_progress" not in st.session_state:
        st.session_state.dfm_progress = st.session_state.dfm.copy()  # Initially show the full DataFrame
    if "df_progress" not in st.session_state:
        st.session_state.df_progress = st.session_state.df.copy()  # Initially show the full DataFrame
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False  # Auto-refresh toggle
    if "rows_added" not in st.session_state:
        st.session_state.rows_added = len(st.session_state.dfm) + 1  # Start with all rows added
    if "total_rows" not in st.session_state:
        st.session_state.total_rows = len(st.session_state.dfm) + 1  # Total rows in the DataFrame
    if "dataframe_history" not in st.session_state:
        st.session_state.dataframe_history = []  # List to store the last 4 dataframes
    if "machine_utilization_history" not in st.session_state:
        st.session_state.machine_utilization_history = []  # List to store machine utilization dataframes
    if "component_waiting_history" not in st.session_state:
        st.session_state.component_waiting_history = []  # List to store component waiting time dataframes
    if "product_waiting_history" not in st.session_state:
        st.session_state.product_waiting_history = []  # List to store product waiting time dataframes
    if "late_df_history" not in st.session_state:
        st.session_state.late_df_history = []  # List to store late products dataframes

    # Layout for buttons
    with st.container():
        col1, spacer1, col2, spacer2, col3, spacer3, col4 = st.columns([1, 0.2, 1, 0.2, 1, 0.2, 1])

        with col1:
            if st.button("Start"):
                if not st.session_state.auto_refresh:  # If not already animating
                    if st.session_state.rows_added == 0:  # If starting fresh
                        # Initialize the progress DataFrame
                        st.session_state.dfm_progress = pd.DataFrame(columns=st.session_state.dfm.columns)

                        st.session_state.machine_schedule = defaultdict(list)
                        for machine in st.session_state.df['Machine Number'].unique():
                            st.session_state.machine_schedule[machine].append(
                                (st.session_state.df['Order Processing Date'].min().replace(hour=9, minute=0),
                                 st.session_state.df['Order Processing Date'].min().replace(hour=9, minute=0),
                                 None))

                        st.session_state.machine_last_end = defaultdict(
                            lambda: st.session_state.df['Order Processing Date'].min().replace(hour=9, minute=0))
                        # Extract machine state for rows up to `st.session_state.rows_added`
                        for _, row in st.session_state.dfm.iloc[:st.session_state.rows_added].iterrows():
                            st.session_state.machine_schedule[row['Machine Number']].append(
                                (row['Start Time'], row['End Time'], row['UniqueID']))
                            st.session_state.machine_last_end[row['Machine Number']] = max(
                                st.session_state.machine_last_end[row['Machine Number']], row['End Time'])

                    st.session_state.auto_refresh = True  # Enable auto-refresh
        with col2:
            if st.button("Pause"):
                st.session_state.auto_refresh = False
                st.session_state.rows_added -= 1
                st.info("Animation paused.")
        with col3:
            if st.button("Reschedule"):
                pause_index = st.session_state.rows_added  # Use current progress as the pause index
                # Extract scheduled and unscheduled parts
                dfm1 = st.session_state.dfm.iloc[:pause_index].copy().reset_index(drop=True)  # Scheduled portion
                dfm2 = st.session_state.dfm.iloc[pause_index:].copy().sort_values(
                    by=['Start Time', 'End Time', 'Promised Delivery Date']
                ).reset_index(drop=True)  # Remaining unscheduled portion

                # Reset unscheduled rows
                dfm2['Start Time'] = pd.NaT
                dfm2['End Time'] = pd.NaT

                # Reschedule using the existing state
                dfm2 = reschedule_production_with_days(dfm2, st.session_state.machine_last_end,
                                                      st.session_state.machine_schedule, dfm1)
                dfm2 = adjust_end_time_and_start_time(dfm2).sort_values(
                    by=['Start Time', 'End Time', 'Promised Delivery Date'])
                # Combine both parts
                new_dataframe = pd.concat([dfm1, dfm2], ignore_index=True)

                # Append the new dataframe to the history list
                st.session_state.dataframe_history.append(new_dataframe)

                # Calculate derived dataframes
                machine_utilization_df = calculate_machine_utilization(new_dataframe.copy())
                component_waiting_df = calculate_waiting_time(new_dataframe, group_by_column='Components', date_columns=('Order Processing Date', 'Start Time'))
                product_waiting_df = calculate_waiting_time(new_dataframe, group_by_column='Product Name', date_columns=('Order Processing Date', 'Start Time'))
                late_df = late_products(new_dataframe)

                # Append derived dataframes to their history lists
                st.session_state.machine_utilization_history.append(machine_utilization_df)
                st.session_state.component_waiting_history.append(component_waiting_df)
                st.session_state.product_waiting_history.append(product_waiting_df)
                st.session_state.late_df_history.append(late_df)

                # Ensure only the last 4 dataframes are retained
                if len(st.session_state.dataframe_history) > 4:
                    st.session_state.dataframe_history.pop(0)  # Remove the oldest dataframe
                    st.session_state.machine_utilization_history.pop(0)
                    st.session_state.component_waiting_history.pop(0)
                    st.session_state.product_waiting_history.pop(0)
                    st.session_state.late_df_history.pop(0)

                st.session_state.rows_added = pause_index  # Restart animation from the current index
                st.info("Rescheduling initiated. Click 'Start' to animate again.")
        with col4:
            if st.button("Reset"):
                st.session_state.dfm_progress = pd.DataFrame(columns=st.session_state.dfm.columns)  # Empty progress DataFrame
                st.session_state.rows_added = 0
                st.session_state.auto_refresh = False
                st.session_state.machine_schedule = None
                st.session_state.machine_last_end = None
                if 'df_scatter_progress' in st.session_state:
                    st.session_state.df_scatter_progress = st.session_state.dfm.copy().reset_index(drop=True)
                st.success("Progress reset successfully.")

        st.write(f'{st.session_state.rows_added + 1}th step')

    # Progressive animation
    if st.session_state.auto_refresh and st.session_state.rows_added < st.session_state.total_rows:
        st_autorefresh(interval=2000, limit=None, key="autorefresh")  # Refresh every second
        # Add the next row to the progress DataFrame
        st.session_state.dfm_progress = pd.concat(
            [st.session_state.dfm_progress, st.session_state.dfm.iloc[st.session_state.rows_added:st.session_state.rows_added + 1]],
            ignore_index=True
        )
        st.session_state.rows_added += 1  # Increment the counter

    # Stop animation when all rows are added
    if st.session_state.rows_added >= st.session_state.total_rows:
        st.session_state.auto_refresh = False
        st.success("Animation complete! Reload the page to reset.")

    col1, col2 = st.columns(2)

    # =========================================================================================

    with col1:
        # Gantt Chart
        st.markdown("### Gantt Chart")
        if st.session_state.auto_refresh == False:
            # Static Gantt chart displayed immediately when the page loads
            if not st.session_state.auto_refresh:  # Show the static chart if not animating
                fig_static = px.timeline(
                    st.session_state.dfm_progress,
                    x_start="Start Time",
                    x_end="End Time",
                    y="Product Name",
                    color="legend",  # Use Components for color differentiation
                    labels={"Components": "Component", "Machine Number": "Machine"}
                )
                fig_static.update_yaxes(categoryorder="total ascending")  # Sort tasks
                fig_static.update_layout(
                    legend_title="Component",
                    xaxis_title="Time",
                    yaxis_title="Products"
                )
                # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
                st.plotly_chart(fig_static, use_container_width=True, key='gantt_chart_static')
                # st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Display the progressive Gantt chart during animation
            # st.markdown('<div class="visualization-container">', unsafe_allow_html=True)
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
                # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
                st.plotly_chart(fig_static, use_container_width=True, key='gantt_chart_animated')
                # st.markdown('</div>', unsafe_allow_html=True)
        
# =========================================================================================
    
        # elif selected_visualization == "Gantt Chart (Unscheduled)":        
        # Gantt Chart (Unscheduled)
        st.markdown("### Gantt Chart (Unscheduled)")
        data = st.session_state.dfm.copy()  # Ensure the original DataFrame is not modified
        data['Duration'] = data['Quantity Required'] / 1000 * data['Run Time (min/1000)']
        
        # Adjust durations for working hours and days
        data['Adjusted End Time'] = data.apply(
            lambda row: adjust_to_working_hours_and_days(row['Order Processing Date'], row['Duration']),
            axis=1)
        
        # Create a horizontal bar chart
        gcu_static = px.bar(
            data,
            x="Duration",  # Horizontal axis
            y="Product Name",  # Vertical axis
            color="legend",  # Color by components
            orientation="h",  # Horizontal bars
            labels={"Duration": "Task Duration (minutes)", "Product Name": "Product", "Components": "Component"},
        )

        gcu_static.update_layout(
            xaxis_title="Task Duration (minutes)",
            yaxis_title="Products",
            legend_title="Components",
            template="plotly_white"
        )

        # Integrate into Streamlit
        # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.plotly_chart(gcu_static, use_container_width=True, key='gantt_chart_unscheduled')
        # st.markdown('</div>', unsafe_allow_html=True)
        
# =========================================================================================

        # elif selected_visualization == "Product Waiting Time":
        # Create a bar chart
        st.markdown("### Product Waiting Time")
        fig = px.bar(
            st.session_state.product_waiting_df,
            x="Product Name",
            y="Average Days",
            text="Formatted Time",
            # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
            title="Average Product Waiting Time",
            color="Product Name",
        )

        # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            xaxis_title="Product Name",
            yaxis_title="Waiting Time",
            template="plotly_white",
            showlegend=True,
        )

        # Integrate into Streamlit
        # st.title("Machine Utilization Visualization")
        # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key='product_waiting_time')
        # st.markdown('</div>', unsafe_allow_html=True)
        
    # =========================================================================================

    with col2:
        # Product Components Status
        st.markdown("### Product Components Status")
        if "df_scatter_progress" not in st.session_state:
            st.session_state.df_scatter_progress = st.session_state.dfm.copy().reset_index(drop=True)  # Independent copy for scatter plot
        st.session_state.df_scatter_progress.index = range(1, len(st.session_state.df_scatter_progress) + 1)

        # Process the current row for the scatter plot
        current_row_index = st.session_state.rows_added  # Sync progression with Gantt chart
        if current_row_index < len(st.session_state.df_scatter_progress):
            # Get the current row to process
            current_row = st.session_state.df_scatter_progress.iloc[current_row_index]

            # Update status for the current row based on scatter plot's logic
            if pd.notna(current_row['End Time']) and pd.notna(current_row['Promised Delivery Date']):
                if current_row['Process Type'] == 'Outsource' and current_row['End Time'] < current_row['Promised Delivery Date']:
                    st.session_state.df_scatter_progress.at[current_row_index, 'status'] = 'Completed_Outsource'
                elif current_row['Process Type'] == 'In House' and current_row['End Time'] < current_row['Promised Delivery Date']:
                    st.session_state.df_scatter_progress.at[current_row_index, 'status'] = 'Completed_In House'
                elif current_row['End Time'] > current_row['Promised Delivery Date']:
                    st.session_state.df_scatter_progress.at[current_row_index, 'status'] = 'Late'

        # Assign colors for scatter plot
        status_colors = {
            'InProgress_Outsource': 'gray',
            'InProgress_In House': 'dimgray',
            'Completed_Outsource': '#FB8A12',
            'Completed_In House': '#FFA515',
            'Late': 'red'
        }
        st.session_state.df_scatter_progress['color'] = st.session_state.df_scatter_progress['status'].map(status_colors)

        # Create scatter plot
        fig = go.Figure()

        for _, row in st.session_state.df_scatter_progress.iterrows():
            fig.add_trace(go.Scatter(
                x=[row['Product Name']],
                y=[row['Components']],
                mode='markers+text',
                marker=dict(size=20, color=row['color'], symbol='square'),
                text=row['Machine Number'],  # Display machine info
                textposition='top center',
                name=row['status'],  # Controls legend label
                legendgroup=row['status'],  # Groups traces with the same status
                showlegend=not fig.data or row['status'] not in [trace.name for trace in fig.data]  # Show legend once per status
            ))

        fig.update_layout(
            xaxis=dict(title="Product Name"),
            yaxis=dict(title="Components"),
            legend_title="Status and Process Type",
            template="plotly_white"
        )

        # Display the scatter plot
        # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key='product_component_status')
        # st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================================
 
        # elif selected_visualization == "Machine Utilisation":
        # Calculate machine utilization
        st.markdown("### Machine Utilisation")
        average_utilization = calculate_machine_utilization(st.session_state.dfm)

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
            showlegend=True,
        )

        # Integrate into Streamlit
        # st.title("Machine Utilization Visualization")
        # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key='machine_utilisation')
        # st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================================
    
        # elif selected_visualization == "Component Waiting Time":
        # Create a bar chart
        st.markdown("### Component Waiting Time")
        fig = px.bar(
            st.session_state.component_waiting_df,
            x="Components",
            y="Average Days",
            text="Formatted Time",
            # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
            title="Average Components Waiting Time",
            color="Components",
        )

        # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            xaxis_title="Components",
            yaxis_title="Waiting Time",
            template="plotly_white",
            showlegend=True,
        )

        # Integrate into Streamlit
        # st.title("Machine Utilization Visualization")
        # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key='component_waiting_time')
        # st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================================
