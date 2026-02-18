import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & Advanced Custom Styling
st.set_page_config(page_title="AMS - Smart Substitution", layout="wide")

# High-quality School Background with Color Harmony
BG_URL = "https://images.unsplash.com/photo-1541339907198-e08756ebafe3?q=80&w=2070&auto=format&fit=crop"

st.markdown(f"""
<style>
/* Background with smooth overlay */
[data-testid="stAppViewContainer"] {{
    background-image: url("{BG_URL}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(245, 247, 249, 0.9); /* Soft professional gray-white */
    z-index: 0;
}}

.main .block-container {{
    position: relative;
    z-index: 1;
}}

/* Typography: Deep Navy for high readability */
h1, h2, h3, p, span, label {{
    color: #1A365D !important; /* Professional Navy Blue */
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* Card Elements: Elevated White Design */
.stDataFrame, div[data-testid="stVerticalBlock"] > div {{
    background-color: #FFFFFF !important;
    border-radius: 16px !important;
    border: 1px solid #E2E8F0 !important;
    padding: 15px !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05) !important;
}}

/* Sidebar: Clean & Organized */
[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid #E2E8F0;
}}

/* Buttons: Cohesive Color Palette */
.stButton>button {{
    background: linear-gradient(90deg, #2D3748 0%, #4A5568 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    transition: all 0.3s ease;
}}

.stButton>button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}}

/* Success/Confirm Button */
div.stButton > button:first-child {{
    background: linear-gradient(90deg, #38A169 0%, #2F855A 100%) !important;
}}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Smart Substitution System - Al-Alamia School")

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
        st.session_state.used_today = []
    except:
        st.error("⚠️ Connection Error: Please verify your Cloud Secrets.")
        st.stop()

# 3. Main Interface
try:
    st.sidebar.header("🕹️ Administration")
    day = st.sidebar.selectbox("Select Active Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # Load daily schedule
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader(f"🗓️ ELA Teachers' Schedule - {day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("Identify Absent Teacher:", day_df['Teacher_Name'].dropna().unique())
    session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
    target_session = st.sidebar.selectbox("Select Target Session:", session_cols)

    # Filtering Engine
    available = []
    for _, row in day_df.iterrows():
        workload = sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))
        if (str(row[target_session]).lower() == 'free' and workload < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 AI-Recommended Substitutes for {target_session}")
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("🔀 Reshuffle List"): random.shuffle(available)
    with c1:
        sub_t = st.selectbox("Assign Candidate:", available) if available else st.warning("No matches available for this session.")

    if sub_t and st.button("✅ Confirm Assignment & Sync"):
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        st.session_state.used_today.append(sub_t)
        
        try:
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("✅ Cloud Database Synchronized Successfully!")
        except:
            st.warning("⚠️ Local Update Only (Check Write Permissions).")
        st.balloons()

    # 4. Net Balance Performance Dashboard
    st.divider()
    st.subheader("📊 Teacher Performance Ledger (Net Balance)")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    
    # Elegant Data Presentation
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#E53E3E" if v < 0 else "#38A169" if v > 0 else "#2D3748"}; font-weight: bold', subset=['Net']
    ), use_container_width=True)

    # Action Footer
    st.divider()
    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Export Updated Records (CSV)",
        data=csv,
        file_name=f"AMS_Substitution_Report_{day}.csv",
        mime="text/csv",
    )

except Exception as e:
    st.error(f"Operational Error: {e}")
