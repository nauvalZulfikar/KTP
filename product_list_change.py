import pandas as pd
import streamlit as st

def product_list_change():
    prod_chg = st.session_state.dfm.copy()

    st.title("Product List Management")
    
    # Add Tabs Below
    tabs = st.tabs([
        "Add Products", 
        "Delete Products", 
        "Change Due Date"
    ])

    if 'dfm' in st.session_state:
        with tabs[0]:
            existing_prod = prod_chg['Product Name'].unique()

            try:
                add_prod = st.text_input("New Product Name:")
                
                if add_prod in existing_prod:
                    next_serial = prod_chg.loc[prod_chg['Product Name']==add_prod,'Sr. No'].unique()[0]
                    next_ordDate = prod_chg.loc[prod_chg['Product Name']==add_prod,'Order Processing Date'].unique()[0]
                    next_devDate = prod_chg.loc[prod_chg['Product Name']==add_prod,'Promised Delivery Date'].unique()[0]
                    next_quantReq = prod_chg.loc[prod_chg['Product Name']==add_prod,'Quantity Required'].unique()[0]
                    next_comp = 'C'+str(int((prod_chg.loc[prod_chg['Product Name']==add_prod,'Components'].max())[-1])+1)
                    next_ops = 'Op'+str(int((prod_chg.loc[prod_chg['Product Name']==add_prod,'Operation'].max())[-1])+1)
                else:
                    next_serial = int(add_prod.split(' ')[1])
                    next_ordDate = pd.to_datetime(st.date_input("New Order Processing Date:"))
                    next_devDate = pd.to_datetime(st.date_input("New Promised Delivery Date:"))
                    next_quantReq = st.text_input("New Quantity Required:")
                    next_comp = 'C1'
                    next_ops = 'Op1'
                    
                add_proc = st.selectbox("New Process Type:",["In House","OutSource"])
                if add_proc == 'In House':
                    inhouse = prod_chg.loc[prod_chg['Process Type']=='In House','Machine Number'].unique()
                    add_mac = st.selectbox("New Machine Number:",inhouse)
                else:
                    add_mac = st.selectbox("New Machine Number:",['OutSrc'])
                
                add_run = st.text_input("New Run Time (min/1000):")
                add_cycle = st.text_input("New Cycle Time (seconds):")
                add_setup = st.text_input("New Setup Time (seconds):")
                add_legend = next_comp if add_mac != 'OutSrc' else 'OutSrc'
                next_uniqueID = prod_chg['UniqueID'].max()+1
            except:
                pass
            
            if st.button("Submit"):
                new_row = pd.DataFrame({
                    'UniqueID': [int(next_uniqueID)],
                    'Sr. No': [int(next_serial)],
                    'Product Name': [add_prod],
                    'Order Processing Date': [next_ordDate],
                    'Promised Delivery Date': [next_devDate],
                    'Quantity Required': [int(next_quantReq)],
                    'Components': [next_comp],
                    'Operation': [next_ops],
                    'Process Type': [add_proc],
                    'Machine Number': [add_mac],
                    'Run Time (min/1000)': [int(add_run)],
                    'Cycle Time (seconds)': [float(add_cycle)],
                    'Setup time (seconds)': [int(add_setup)],
                    'legend': [add_legend]
                })
                
                st.session_state.df  = pd.concat([st.session_state.df,new_row])
                st.session_state.dfm = pd.concat([st.session_state.dfm,new_row])  
                st.success(f"Product '{add_prod}' added successfully.")
                
            st.dataframe(st.session_state.dfm)

            with pd.ExcelWriter('Product Details_v1.xlsx', engine='openpyxl') as writer:
                st.session_state.df.to_excel(writer, sheet_name='P', index=False)
                st.session_state.dfm.to_excel(writer, sheet_name='prodet', index=False)
                st.session_state.machine_utilization_df.to_excel(writer, sheet_name='Machine Utilisation')
                st.session_state.product_waiting_df.to_excel(writer, sheet_name='Product Waiting Time')
                st.session_state.component_waiting_df.to_excel(writer, sheet_name='Component Waiting Time')
                st.session_state.late_df.to_excel(writer, sheet_name='Late Products')

        with tabs[1]:
            del_prod = st.text_input("Delete Product Name:")
            prod_chg = prod_chg[prod_chg['Product Name']!=del_prod]

            if st.button("Delete"):
                st.session_state.df = st.session_state.df[st.session_state.df['Product Name']!=del_prod].reset_index(drop=True)
                st.session_state.dfm = st.session_state.dfm[st.session_state.dfm['Product Name']!=del_prod].reset_index(drop=True)
                st.warning(f"Product with ID '{del_prod}' deleted successfully.")
                
            st.dataframe(st.session_state.dfm)

            with pd.ExcelWriter('Product Details_v1.xlsx', engine='openpyxl') as writer:
                st.session_state.df.to_excel(writer, sheet_name='P', index=False)
                st.session_state.dfm.to_excel(writer, sheet_name='prodet', index=False)
                st.session_state.machine_utilization_df.to_excel(writer, sheet_name='Machine Utilisation')
                st.session_state.product_waiting_df.to_excel(writer, sheet_name='Product Waiting Time')
                st.session_state.component_waiting_df.to_excel(writer, sheet_name='Component Waiting Time')
                st.session_state.late_df.to_excel(writer, sheet_name='Late Products')
        
        with tabs[2]:
            chg_prod = st.text_input('Change Product Name:')
            chg_prom = pd.to_datetime(st.date_input("Change Promised Delivery Date:")).strftime('%Y-%m-%d')

            if st.button("Confirm"):
                st.session_state.df.loc[st.session_state.df['Product Name']==chg_prod,'Promised Delivery Date'] = chg_prom
                st.session_state.dfm.loc[st.session_state.dfm['Product Name']==chg_prod,'Promised Delivery Date'] = chg_prom
                st.info(f"Product {chg_prod}'s Product Delivery date had been changed to {chg_prom}")
                
            st.dataframe(st.session_state.dfm)

            with pd.ExcelWriter('Product Details_v1.xlsx', engine='openpyxl') as writer:
                st.session_state.df.to_excel(writer, sheet_name='P', index=False)
                st.session_state.dfm.to_excel(writer, sheet_name='prodet', index=False)
                st.session_state.machine_utilization_df.to_excel(writer, sheet_name='Machine Utilisation')
                st.session_state.product_waiting_df.to_excel(writer, sheet_name='Product Waiting Time')
                st.session_state.component_waiting_df.to_excel(writer, sheet_name='Component Waiting Time')
                st.session_state.late_df.to_excel(writer, sheet_name='Late Products')
