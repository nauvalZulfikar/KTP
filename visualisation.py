import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import streamlit as st
from collections import defaultdict
from scheduler import adjust_to_working_hours_and_days, calculate_machine_utilization, adjust_end_time_and_start_time, schedule_production_with_days, reschedule_production_with_days, calculate_waiting_time, late_products
import time

# Function to create a vertical divider
def vertical_divider():
    st.markdown(
        """ 
        <style>
            .divider {
                display: inline-block;
                width: 1px;
                background-color: white;
                height: 100%;
                margin: 0 10px;
            }
        </style>
        <div class="divider"></div>
        """, unsafe_allow_html=True
    )

# Function to create a horizontal divider
def horizontal_divider():
    st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

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
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False  # Auto-refresh toggle
    if "rows_added" not in st.session_state:
        st.session_state.rows_added = len(st.session_state.dfm) + 1  # Start with all rows added
    if "total_rows" not in st.session_state:
        st.session_state.total_rows = len(st.session_state.dfm) + 1  # Total rows in the DataFrame
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

                dfm2 = dfm2.groupby('UniqueID',as_index=False).agg({
                    'Sr. No':'first',
                    'Product Name':'first',
                    'Order Processing Date':'first',
                    'Promised Delivery Date':'first',
                    'Quantity Required':"sum",
                    'Components':'first',
                    'Operation':'first',
                    'Process Type':'first',
                    'Machine Number':'first',
                    'Run Time (min/1000)':'first',
                    'Cycle Time (seconds)':'first',
                    'Setup time (seconds)':'first',
                    'Start Time':'first',
                    'End Time':'first',
                    'status':'first',
                    # 'Status':'first',
                    'legend':'first'
                    })

                # Reschedule using the existing state
                dfm2 = reschedule_production_with_days(dfm2, st.session_state.machine_last_end,
                                                      st.session_state.machine_schedule, dfm1)
                dfm2 = adjust_end_time_and_start_time(dfm2).sort_values(
                    by=['Start Time', 'End Time', 'Promised Delivery Date'])
                # Combine both parts
                new_dataframe = pd.concat([dfm1, dfm2], ignore_index=True)
                new_dataframe = new_dataframe[new_dataframe['Quantity Required']>=1]

                # Append the new dataframe to the history list
                st.session_state.dfm = new_dataframe.reset_index(drop=True).copy()
                st.session_state.dataframe_history.append(new_dataframe)
                #

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
                
                # ✅ Clear stored visualization state
                if "df_scatter_progress" in st.session_state:
                    del st.session_state.df_scatter_progress  
                if "last_static_status" in st.session_state:
                    del st.session_state.last_static_status  

                st.success("Progress reset successfully.")


        st.write(f'{st.session_state.rows_added + 1}th step')
    
    if "dfm_progress" not in st.session_state:
        # st.session_state.dfm_progress = st.session_state.dfm.copy()  # Initially show the full DataFrame
        st.session_state.dfm_progress = st.session_state.dfm.copy()  # Initially show the full DataFrame
    if "df_progress" not in st.session_state:
        st.session_state.df_progress = st.session_state.df.copy()  # Initially show the full DataFrame
    if "dataframe_history" not in st.session_state:
        st.session_state.dataframe_history = []  # List to store the last 4 dataframes

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

    # =========================================================================================

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
                labels={"Components": "Component", "Machine Number": "Machine"},
                hover_data=["Machine Number"]
            )
            fig_static.update_yaxes(categoryorder="total ascending")  # Sort tasks
            fig_static.update_layout(
                legend_title="Component",
                xaxis_title="Time",
                yaxis_title="Products"
            )
            st.plotly_chart(fig_static, use_container_width=True, key='gantt_chart_static')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    else:
        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            fig_animated = px.timeline(
                st.session_state.dfm_progress,
                x_start="Start Time",
                x_end="End Time",
                y="Product Name",
                color="legend",  # Use Components for color differentiation
                labels={"Components": "Component", "Machine Number": "Machine"},
                hover_data=["Machine Number"]
            )
            fig_animated.update_yaxes(categoryorder="total ascending")  # Sort tasks
            fig_animated.update_layout(
                legend_title="Component",
                xaxis_title="Time",
                yaxis_title="Products"
            )
            # st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            st.plotly_chart(fig_animated, use_container_width=True, key='gantt_chart_animated')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

    # =========================================================================================

    # Product Components Status
    st.markdown("### Product Components Status")
    # Ensure scatter plot uses the latest dfm_progress data
    df_scatter_progress = st.session_state.dfm_progress.copy()

    # ✅ Function to Generate Scatter Plot
    def generate_scatter_plot(data, key_name):
        fig = go.Figure()
        
        for i in range(len(data)):
            row = data.iloc[i]
            marker_symbol = 'circle' if row['Process Type'] == 'Outsource' else 'square'

            fig.add_trace(go.Scatter(
                x=[row['Product Name']],
                y=[row['Components']],
                mode='markers+text',
                marker=dict(size=20, color=row['color'], symbol=marker_symbol),
                text=row['Machine Number'],
                textposition='top center',
                name=row['status'],
                legendgroup=row['status'],
                showlegend=not fig.data or row['status'] not in [trace.name for trace in fig.data]
            ))

        fig.update_layout(
            xaxis=dict(title="Product Name"),
            yaxis=dict(title="Components"),
            legend_title="Status and Process Type",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True, key=key_name)

    # ✅ Step 1: Assign Colors Based on Status
    status_colors = {
        'InProgress': 'orange',
        'Completed': 'green',
        'Late': 'red'
    }

    # ✅ Step 2: If Animation is Running, Update Status Dynamically
    if st.session_state.auto_refresh:
        st.subheader("Animated Product Component Status")

        for i in range(len(df_scatter_progress)):
            row = df_scatter_progress.iloc[i]

            if pd.notna(row['End Time']) and pd.notna(row['Promised Delivery Date']):
                if row['End Time'] < row['Promised Delivery Date']:
                    df_scatter_progress.at[i, 'status'] = 'Completed'
                else:
                    df_scatter_progress.at[i, 'status'] = 'Late'
            else:
                df_scatter_progress.at[i, 'status'] = 'InProgress'

        df_scatter_progress['color'] = df_scatter_progress['status'].map(status_colors)

        # ✅ Store the latest computed status for later use
        st.session_state.last_static_status = df_scatter_progress.copy()

        # ✅ Display Animated Scatter Plot
        generate_scatter_plot(df_scatter_progress, key_name="product_component_status_animated")

    # ✅ Step 3: If Animation Stops, Keep Last Updated Status Instead of Resetting
    else:
        st.subheader("Static Product Component Status")

        if "last_static_status" in st.session_state:
            df_scatter_progress = st.session_state.last_static_status  # Keep last updated statuses
        else:
            df_scatter_progress["status"] = "InProgress"  # Fallback for first load

        df_scatter_progress['color'] = df_scatter_progress['status'].map(status_colors)

        # ✅ Display Static Scatter Plot (With Last Animation Status)
        generate_scatter_plot(df_scatter_progress, key_name="product_component_status_static")

    st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    
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
    st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

# =========================================================================================

    # Calculate machine utilization
    st.markdown("### Machine Utilisation")
    average_utilization = calculate_machine_utilization(st.session_state.dfm_progress)

    # Prepare data for visualization
    utilization_df = average_utilization.reset_index()
    utilization_df.columns = ["Machine Number", "Average Utilization"]
    utilization_df["Average Utilization (%)"] = utilization_df["Average Utilization"] * 100

    if st.session_state.auto_refresh == False:
        # Static Gantt chart displayed immediately when the page loads
        if not st.session_state.auto_refresh:  # Show the static chart if not animating
            mu_static = px.bar(
                utilization_df,
                x="Machine Number",
                y="Average Utilization (%)",
                text="Average Utilization (%)",
                labels={"Average Utilization (%)": "Utilization (%)", "Machine Number": "Machine"},
                color="Machine Number",
            )

            mu_static.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            mu_static.update_layout(
                xaxis_title="Machine",
                yaxis_title="Utilization (%)",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(mu_static, use_container_width=True, key='machine_utilisation_static')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    else:
        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            mu_animated = px.bar(
                utilization_df,
                x="Machine Number",
                y="Average Utilization (%)",
                text="Average Utilization (%)",
                labels={"Average Utilization (%)": "Utilization (%)", "Machine Number": "Machine"},
                color="Machine Number",
            )

            mu_animated.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            mu_animated.update_layout(
                xaxis_title="Machine",
                yaxis_title="Utilization (%)",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(mu_animated, use_container_width=True, key='machine_utilisation_animated')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

# =========================================================================================

    # Calculate machine utilization
    st.markdown("### Product Waiting Time")
    product_waiting = calculate_waiting_time(st.session_state.dfm_progress, group_by_column='Product Name', date_columns=('Order Processing Date', 'Start Time'))
    
    if st.session_state.auto_refresh == False:
        # Static Gantt chart displayed immediately when the page loads
        if not st.session_state.auto_refresh:  # Show the static chart if not animating
            pw_static = px.bar(
                product_waiting,
                x="Product Name",
                y="Average Days",
                text="Formatted Time",
                # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
                # title="Average Product Waiting Time",
                color="Product Name",
            )

            # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            pw_static.update_layout(
                xaxis_title="Product Name",
                yaxis_title="Waiting Time",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(pw_static, use_container_width=True, key='product_waiting_time_static')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    else:
        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            pw_animated = px.bar(
                product_waiting,
                x="Product Name",
                y="Average Days",
                text="Formatted Time",
                # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
                # title="Average Product Waiting Time",
                color="Product Name",
            )

            # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            pw_animated.update_layout(
                xaxis_title="Product Name",
                yaxis_title="Waiting Time",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(pw_animated, use_container_width=True, key='product_waiting_time_animated')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

# =========================================================================================

    # Calculate machine utilization
    st.markdown("### Component Waiting Time")
    component_waiting = calculate_waiting_time(st.session_state.dfm_progress, group_by_column='Components', date_columns=('Order Processing Date', 'Start Time'))
    
    if st.session_state.auto_refresh == False:
        # Static Gantt chart displayed immediately when the page loads
        if not st.session_state.auto_refresh:  # Show the static chart if not animating
            cw_static = px.bar(
                component_waiting,
                x="Components",
                y="Average Days",
                text="Formatted Time",
                labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
                color="Components",
            )

            # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            cw_static.update_layout(
                xaxis_title="Components",
                yaxis_title="Waiting Time",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(cw_static, use_container_width=True, key='component_waiting_time_static')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    else:
        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            cw_animated = px.bar(
                component_waiting,
                x="Components",
                y="Average Days",
                text="Formatted Time",
                labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
                color="Components",
            )

            # fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            cw_animated.update_layout(
                xaxis_title="Components",
                yaxis_title="Waiting Time",
                template="plotly_white",
                showlegend=True,
            )

            # Integrate into Streamlit
            st.plotly_chart(cw_animated, use_container_width=True, key='component_waiting_time_animated')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)

# =========================================================================================

    # elif selected_visualization == "Component Waiting Time":
    # Create a bar chart
    st.markdown("### Late Products")
    product_late = late_products(st.session_state.dfm_progress)

    if st.session_state.auto_refresh == False:
        # Static Gantt chart displayed immediately when the page loads
        if not st.session_state.auto_refresh:  # Show the static chart if not animating
            lp_static = px.pie(
                # st.session_state.late_df,
                product_late,
                values="count",
                names="late",
                # text="late",
                # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
                title="Number of Late Products",
                color="count",
            )
            # Update trace to show both percentage and actual number
            lp_static.update_traces(
                textinfo="label+percent+value",  # Show category name, percentage, and absolute value
                texttemplate="%{percent:.1%} (%{value})",  # Format: Label: Value (Percentage)
                textposition="inside",  # Position labels inside the slices
            )

            # Update layout
            lp_static.update_layout(
                template="plotly_white",
                showlegend=True,
            )

            st.plotly_chart(lp_static, use_container_width=True, key='late_products_static')
            st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
    else:
        # Display the progressive Gantt chart during animation
        if st.session_state.auto_refresh or st.session_state.rows_added < st.session_state.total_rows:
            lp_animated = px.pie(
            # st.session_state.late_df,
            product_late,
            values="count",
            names="late",
            # text="late",
            # labels={"Average Days": "Utilization (%)", "Machine Number": "Machine"},
            title="Number of Late Products",
            color="count",
        )

        # Update trace to show both percentage and actual number
        lp_animated.update_traces(
            textinfo="label+percent+value",  # Show category name, percentage, and absolute value
            texttemplate="%{percent:.1%} (%{value})",  # Format: Label: Value (Percentage)
            textposition="inside",  # Position labels inside the slices
        )

        # Update layout
        lp_animated.update_layout(
            template="plotly_white",
            showlegend=True,
        )

        st.plotly_chart(lp_animated, use_container_width=True, key='late_products_animated')
        st.markdown('<hr style="border:1px solid white">', unsafe_allow_html=True)
