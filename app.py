import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & Modern Dashboard Style
st.set_page_config(page_title="AMS - ELA Substitution System", layout="wide")

st.markdown(f"""
<style>
    /* Global Background: Modern Neutral Gray */
    [data-testid="stAppViewContainer"] {{
        background-color: #F0F2F5;
    }}
    
    /* Modern Card Container */
    .main .block-container {{
        background-color: transparent;
        padding-top: 2rem;
    }}

    /* Headers: Deep Navy */
    h1, h2, h3 {{
        color: #0F172A !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700 !important;
    }}

    /* Card Styling: White with crisp borders */
    .stDataFrame, .sub-box, div[data-baseweb="select"], .stAlert {{
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        padding: 10px;
    }}

    /* Sidebar: Clean White Style */
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }}

    /* Buttons: Professional Indigo Gradient */
    .stButton>button {{
        background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s ease;
    }}
    
    .stButton>button:hover {{
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4) !important;
        transform: translateY(-1px);
    }}

    /* Selectbox highlight */
    div[data-baseweb="select"] {{
        border: 1px solid #4F46E5 !important;
    }}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ ELA Department - Smart Substitution Dashboard")

# 2. Connection Logic
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize Session States
if 'shuffle_key' not in st.session_state: st.session_state.shuffle_key = 0
if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
    except:
        st.error("Connection lost.")
        st.stop()

# 3. Operations Hub
try:
    st.sidebar.markdown("### ⚙️ Settings")
    selected_day = st.sidebar.selectbox("Day Selection", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader("👤 Step 1: Identify Absent Staff")
    all_teachers = day_df['Teacher_Name'].dropna().unique()
    absent_teachers = st.multiselect("Search and select teachers:", all_teachers)

    if absent_teachers:
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("🔀 Reshuffle All"):
                st.session_state.shuffle_seed = random.randint(0, 999)
                st.session_state.shuffle_key += 1
                st.rerun()

        st.divider()
        st.subheader("📋 Step 2: Review Suggested Substitutions")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        total_assignments = {}
        random.seed(st.session_state.shuffle_key)

        for absent_t in absent_teachers:
            with st.expander(f"📍 Substitution Plan for: {absent_t}", expanded=True):
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
                            if (t_name not in absent_teachers and str(row[sess]).lower() == 'free' and workload < 6 and credit < 4 and (sess, t_name) not in total_assignments.items()):
                                possible.append(t_name)
                        
                        chosen_sub = random.choice(possible) if possible else "N/A"
                        st.markdown(f"**{sess}**")
                        final_sub = st.selectbox("Sub:", possible, 
                                                index=possible.index(chosen_sub) if chosen_sub in possible else 0,
                                                key=f"s_{absent_t}_{sess}_{st.session_state.shuffle_key}")
                        total_assignments[f"{absent_t}_{sess}"] = final_sub

        if st.button("🚀 Finalize & Save to Database"):
            # Update Points
            for absent_t in absent_teachers:
                absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
                count = sum(1 for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s]))
                st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += count
            
            for key, sub_name in total_assignments.items():
                if sub_name != "N/A":
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_name, 'Credit'] += 1
            
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("Cloud Synchronized!")
            st.balloons()

    st.divider()
    st.subheader("📊 Live Performance Tracker")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#E11D48" if v < 0 else "#059669" if v > 0 else "#1E293B"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Awaiting input: Select absent teachers from the menu.")
