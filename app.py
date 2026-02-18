import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & UI Professional Style
st.set_page_config(page_title="AMS - Smart Substitution", layout="wide")

# High Stability Background Image URL
BG_URL = "https://images.unsplash.com/photo-1523050853061-830537572251?q=80&w=2070&auto=format&fit=crop"

st.markdown(f"""
<style>
/* Natural Background (Contain) without distorted zoom */
[data-testid="stAppViewContainer"] {{
    background-image: url("{BG_URL}");
    background-size: cover; /* Adjusted to cover for better filling, use 'contain' if you want it smaller */
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}

/* Semi-transparent White Overlay for High Contrast */
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.88); 
    z-index: 0;
}}

.main .block-container {{
    position: relative;
    z-index: 1;
}}

/* Bold English Typography */
h1, h2, h3, p, span, label, .stSelectbox label {{
    color: #000000 !important;
    font-weight: bold !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}}

/* Card Style for Dataframes */
.stDataFrame, div[data-testid="stVerticalBlock"] > div {{
    background-color: white !important;
    border-radius: 12px !important;
    padding: 10px !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
}}

/* Action Buttons */
.stButton>button {{
    background-color: #28a745 !important;
    color: white !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    width: 100%;
    height: 50px;
}}
</style>
""", unsafe_allow_html=True)

st.title("🏫 Smart Substitution System - Al-Alamia School")

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
        # Force column naming to ensure logic works
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
        st.session_state.used_today = []
    except:
        st.error("⚠️ Connection Error: Please check your Secrets or Spreadsheet link.")
        st.stop()

# 3. Main Interface
try:
    st.sidebar.header("🕹️ Controls")
    day = st.sidebar.selectbox("Select Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # Load daily schedule
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader(f"📅 Staff Schedule - {day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("Absent Teacher:", day_df['Teacher_Name'].dropna().unique())
    session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
    target_session = st.sidebar.selectbox("Target Session:", session_cols)

    # Filter substitutes
    available = []
    for _, row in day_df.iterrows():
        workload = sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))
        if (str(row[target_session]).lower() == 'free' and workload < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 Recommended Substitutes ({target_session})")
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("🔀 Shuffle"): random.shuffle(available)
    with c1:
        sub_t = st.selectbox("Substitute Candidate:", available) if available else st.warning("No matches found")

    if sub_t and st.button("✅ Confirm Substitution & Sync"):
        # Points Logic
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        st.session_state.used_today.append(sub_t)
        
        try:
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("✅ Records Synced with Google Sheets!")
        except:
            st.warning("⚠️ Sync failed locally. Check Secrets.")
        st.balloons()

    # 4. Net Balance Dashboard
    st.divider()
    st.subheader("📈 Net Balance Performance")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
