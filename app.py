import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & Professional UI Style
st.set_page_config(page_title="AMS - Smart Substitution System", layout="wide")

# Custom CSS for Natural Background and High Contrast
st.markdown(f"""
<style>
/* Background Setup - Natural Size (No Distorted Zoom) */
[data-testid="stAppViewContainer"] {{
    background-image: url("https://i.ibb.co/v4m3S3v/rs-w-890-cg-true.webp");
    background-size: contain; /* Normal size without over-zooming */
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-color: #f0f2f6; /* Fallback light gray */
}}

/* Semi-transparent Overlay for Text Clarity */
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.88); 
    z-index: 0;
}}

/* Ensure content stays above the overlay */
.main .block-container {{
    position: relative;
    z-index: 1;
}}

/* Bold English Typography */
h1, h2, h3, p, span, label, .stSelectbox label {{
    color: #000000 !important;
    font-weight: bold !important;
}}

/* Card-style Containers for Tables (White with Shadows) */
.stDataFrame, div[data-testid="stVerticalBlock"] > div {{
    background-color: white !important;
    border-radius: 12px !important;
    padding: 10px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
}}

/* Sidebar Style */
[data-testid="stSidebar"] {{
    background-color: rgba(255, 255, 255, 0.95) !important;
}}

/* Action Button Style */
.stButton>button {{
    background-color: #28a745 !important;
    color: white !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    width: 100%;
}}
</style>
""", unsafe_allow_html=True)

st.title("🏫 Smart Substitution System - Al-Alamia School")

# 2. Connection to Google Sheets
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- Data Initialization ---
if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        
        # Enforce Column Names
        new_cols = ['Teacher_Name', 'Debit', 'Credit']
        current_cols = list(df_bal.columns)
        for i in range(min(len(new_cols), len(current_cols))):
            current_cols[i] = new_cols[i]
        df_bal.columns = current_cols
        
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        
        st.session_state.balance_data = df_bal
        st.session_state.used_today = []
    except Exception as e:
        st.error(f"⚠️ Failed to load system data: {e}")
        st.stop()

# 3. Main Dashboard
try:
    st.sidebar.header("🕹️ Controls")
    selected_day = st.sidebar.selectbox("Select Current Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # Load daily schedule (header=1 to skip potential merged titles)
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])

    st.subheader(f"📅 Full Staff Schedule - {selected_day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("Select Absent Teacher:", day_df['Teacher_Name'].unique())
    session_cols = [c for c in day_df.columns if "Session" in c or "P" in c] # Supports P1, P2 format
    sel_sess = st.sidebar.selectbox("Select Session Period:", session_cols)

    # Substitution Engine
    def calculate_workload(row):
        return sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))

    available = []
    for _, row in day_df.iterrows():
        if (str(row[sel_sess]).lower() == 'free' and calculate_workload(row) < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 Available Substitutes for {sel_sess}")
    col_sel, col_shu = st.columns([3, 1])
    with col_shu: 
        if st.button("🔀 Shuffle List"): random.shuffle(available)
    with col_sel:
        sub_t = st.selectbox("Choose Substitute Teacher:", available) if available else st.warning("No matches found")

    if sub_t and st.button("✅ Confirm & Synchronize"):
        # Update Points (Cumulative logic)
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        st.session_state.used_today.append(sub_t)
        
        try:
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("✅ Records updated in Google Sheets!")
        except:
            st.warning("⚠️ Sync failed. Check Secrets for write access.")
        st.balloons()

    # 4. Net Balance Dashboard (Clean Financial View)
    st.divider()
    st.subheader("📈 Net Balance Dashboard")
    res_df = st.session_state.balance_data.copy()
    res_df['Net Balance'] = res_df['Credit'] - res_df['Debit']
    
    # Financial columns only for clarity
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net Balance']].style.applymap(
        lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net Balance']
    ), use_container_width=True)

    # Export
    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📤 Export Updated Report (CSV)", data=csv, file_name=f"AMS_Balance_{selected_day}.csv")

except Exception as e:
    st.error(f"System Error: {e}")
