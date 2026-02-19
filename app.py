import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & Menaitech Inspired UI
st.set_page_config(page_title="AMS - ELA Substitution System", layout="wide")

st.markdown(f"""
<style>
    /* Background: Clean Light Gray/White */
    [data-testid="stAppViewContainer"] {{
        background-color: #F7F9FC;
    }}
    
    /* Header & Typography: Menaitech Blue */
    h1, h2, h3 {{
        color: #004A99 !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-weight: 600 !important;
    }}
    
    /* Global Text: Dark Gray for better readability */
    p, label, .stMarkdown {{
        color: #4A4A4A !important;
    }}

    /* Card Design: White with subtle shadow (Menaitech Style) */
    .stDataFrame, .sub-box, div[data-baseweb="select"], .stAlert {{
        background-color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid #E1E4E8 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }}

    /* Buttons: Corporate Blue Gradient */
    .stButton>button {{
        background: linear-gradient(180deg, #0056B3 0%, #004A99 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
    }}
    
    .stButton>button:hover {{
        background: #003D80 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
    }}

    /* Sidebar: Professional White */
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #E1E4E8;
    }}
</style>
""", unsafe_allow_html=True)

st.title("👨‍🏫 ELA Teachers' Automated Substitution")

# 2. Connection Logic
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {{
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}}

conn = st.connection("gsheets", type=GSheetsConnection)

# Data Initialization
if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{{BASE_URL}}#gid={{TAB_GIDS['Debit & Credit']}}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
        st.session_state.locked_subs = {{}}
        st.session_state.shuffle_seed = 0
    except:
        st.error("Connection Error. Check your Cloud Secrets.")
        st.stop()

# 3. Core Engine
try:
    selected_day = st.sidebar.selectbox("📅 Select Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{{BASE_URL}}#gid={{TAB_GIDS[selected_day]}}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader("👤 Select Absent Teachers")
    all_teachers = day_df['Teacher_Name'].dropna().unique()
    absent_teachers = st.multiselect("Identify teachers who are absent today:", all_teachers)

    if absent_teachers:
        st.divider()
        st.markdown(f"### 🔄 Substitution Plan Matrix (Seed: {{st.session_state.shuffle_seed}})")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        total_assignments = {{}}
        
        # Set the seed for random shuffle to ensure it changes on button click
        random.seed(st.session_state.shuffle_seed)

        for absent_t in absent_teachers:
            st.markdown(f"**📍 Substitutes for: {{absent_t}}**")
            absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
            busy_sessions = [s for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s])]
            
            cols = st.columns(len(busy_sessions)) if busy_sessions else []
            
            for i, sess in enumerate(busy_sessions):
                with cols[i]:
                    possible = []
                    for _, row in day_df.iterrows():
                        t_name = row['Teacher_Name']
                        workload = sum(1 for s in session_cols if str(row[s]).lower() != 'free' and pd.notna(row[s]))
                        credit = st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == t_name, 'Credit'].values[0]
                        
                        if (t_name not in absent_teachers and 
                            str(row[sess]).lower() == 'free' and 
                            workload < 6 and credit < 4 and 
                            (sess, t_name) not in total_assignments.items()):
                            possible.append(t_name)
                    
                    lock_key = f"{{absent_t}}_{{sess}}"
                    
                    # Selection Logic
                    if lock_key not in st.session_state.locked_subs or st.session_state.locked_subs[lock_key] not in possible:
                        st.session_state.locked_subs[lock_key] = random.choice(possible) if possible else "N/A"
                    
                    st.markdown(f"<small style='color:#004A99'>{{sess}}</small>", unsafe_allow_html=True)
                    st.session_state.locked_subs[lock_key] = st.selectbox("Assign:", possible, 
                        index=possible.index(st.session_state.locked_subs[lock_key]) if st.session_state.locked_subs[lock_key] in possible else 0,
                        key=f"select_{{lock_key}}")
                    
                    total_assignments[lock_key] = st.session_state.locked_subs[lock_key]

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔀 Reshuffle All"):
                st.session_state.shuffle_seed += 1
                st.session_state.locked_subs = {{}}
                st.rerun()
        with c2:
            if st.button("🚀 Confirm & Finalize Assignments"):
                for absent_t in absent_teachers:
                    absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
                    session_count = sum(1 for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s]))
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += session_count
                
                for key, sub_name in total_assignments.items():
                    if sub_name != "N/A":
                        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_name, 'Credit'] += 1
                
                conn.update(spreadsheet=f"{{BASE_URL}}#gid={{TAB_GIDS['Debit & Credit']}}", data=st.session_state.balance_data)
                st.success("Cloud Data Synchronized!")
                st.balloons()

    # Views
    st.divider()
    st.subheader("📊 Global Staff Schedule")
    st.dataframe(day_df, use_container_width=True)

    st.subheader("📊 Teacher Performance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {{"#D9534F" if v < 0 else "#5CB85C" if v > 0 else "#004A99"}}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Select teachers to start the automated mapping.")
