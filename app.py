import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Config & Custom Elegant UI Styling
st.set_page_config(page_title="AMS - Multi-Substitution Hub", layout="wide")

st.markdown(f"""
<style>
    /* Background: Ivory White */
    [data-testid="stAppViewContainer"] {{
        background-color: #FFFFF0;
        background-attachment: fixed;
    }}
    
    /* Global Text: Navy Blue */
    h1, h2, h3, p, label, .stMarkdown, .css-10trblm {{
        color: #000080 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: bold !important;
    }}

    /* Sidebar: Ivory White with Navy Text */
    [data-testid="stSidebar"] {{
        background-color: #FFFFF0 !important;
        border-right: 2px solid #87CEEB;
    }}

    /* Cards and Dataframes: Sky Blue Background with Navy Text */
    .stDataFrame, .sub-box, div[data-baseweb="select"] {{
        background-color: #87CEEB !important; 
        border-radius: 12px !important;
        color: #000080 !important;
    }}

    /* Multi-select and Input boxes: Sky Blue */
    div[data-baseweb="tag"] {{
        background-color: #000080 !important;
        color: #87CEEB !important;
    }}
    
    /* Buttons: Sky Blue with Navy Text */
    .stButton>button {{
        background-color: #87CEEB !important;
        color: #000080 !important;
        border: 2px solid #000080 !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        transition: 0.3s;
    }}
    
    .stButton>button:hover {{
        background-color: #000080 !important;
        color: #87CEEB !important;
    }}

    /* Success/Info Messages */
    .stAlert {{
        background-color: #87CEEB !important;
        color: #000080 !important;
        border: 1px solid #000080;
    }}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ ELA Teachers' Multi-Substitution Center")

# 2. Connection Logic
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}
conn = st.connection("gsheets", type=GSheetsConnection)

# Data Initialization
if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
        st.session_state.locked_subs = {}
    except:
        st.error("Connection Error. Check your Cloud Secrets.")
        st.stop()

# 3. Operations Hub
try:
    selected_day = st.sidebar.selectbox("📅 Select Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader("👤 Select All Absent Teachers")
    all_teachers = day_df['Teacher_Name'].dropna().unique()
    absent_teachers = st.multiselect("Search and add absent teachers:", all_teachers)

    if absent_teachers:
        st.divider()
        st.markdown(f"### 🔄 Live Substitution Map ({len(absent_teachers)} Teachers)")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        total_assignments = {}
        
        for absent_t in absent_teachers:
            st.markdown(f"**📍 Substitutes for: {absent_t}**")
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
                    
                    lock_key = f"{absent_t}_{sess}"
                    if lock_key not in st.session_state.locked_subs or st.session_state.locked_subs[lock_key] not in possible:
                        st.session_state.locked_subs[lock_key] = random.choice(possible) if possible else "N/A"
                    
                    st.markdown(f"<small>{sess}</small>", unsafe_allow_html=True)
                    st.session_state.locked_subs[lock_key] = st.selectbox("Assign:", possible, 
                        index=possible.index(st.session_state.locked_subs[lock_key]) if st.session_state.locked_subs[lock_key] in possible else 0,
                        key=f"select_{lock_key}")
                    
                    total_assignments[lock_key] = st.session_state.locked_subs[lock_key]

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔀 Reshuffle All"):
                st.session_state.locked_subs = {}
                st.rerun()
        with c2:
            if st.button("🚀 Confirm & Finalize to Cloud"):
                for absent_t in absent_teachers:
                    absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
                    session_count = sum(1 for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s]))
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += session_count
                
                for key, sub_name in total_assignments.items():
                    if sub_name != "N/A":
                        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_name, 'Credit'] += 1
                
                conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
                st.success("All changes saved successfully!")
                st.balloons()

    # --- Schedules & Ledger ---
    st.divider()
    st.subheader("📊 Global Staff Schedule")
    st.dataframe(day_df, use_container_width=True)

    st.subheader("📊 Points Balance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#FF0000" if v < 0 else "#006400" if v > 0 else "#000080"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Please select teachers to begin the substitution mapping.")
