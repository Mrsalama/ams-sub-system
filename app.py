import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & UI Style (Matching the requested image)
st.set_page_config(page_title="AMS - Smart Substitution System", layout="wide")

# Custom CSS for the New Style
st.markdown(f"""
<style>
/* Background and Overlay */
[data-testid="stAppViewContainer"] {{
    background-image: url("https://i.ibb.co/v4m3S3v/rs-w-890-cg-true.webp");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.7); /* Light overlay like the image */
    z-index: 0;
}}

/* Main Title Style */
.main-title {{
    color: #000000;
    text-align: center;
    font-size: 42px;
    font-weight: bold;
    padding: 20px;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 15px;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}}

/* Cards Style (White containers for tables) */
.stDataFrame, div[data-testid="stVerticalBlock"] > div {{
    background-color: white !important;
    border-radius: 15px !important;
    padding: 10px !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important;
}}

/* Sidebar Styling */
[data-testid="stSidebar"] {{
    background-color: rgba(255, 255, 255, 0.9) !important;
}}

/* Button Styling */
.stButton>button {{
    background-color: #28a745 !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: bold !important;
    width: 100%;
}}

/* Text Colors for visibility */
h1, h2, h3, p, span, label {{
    color: #1a1a1a !important;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏰 Smart Substitution System - Al-Alamia School</div>', unsafe_allow_html=True)

# 2. Connection to Google Sheets
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- Data Initialization (Smart Handling) ---
if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        
        # Force column naming
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
        st.error(f"⚠️ Failed to load balance data: {e}")
        st.stop()

# 3. Sidebar Controls
st.sidebar.header("⚙️ Control Panel")
selected_day = st.sidebar.selectbox("Select Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])

try:
    # Load daily schedule
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])

    # Display Daily Schedule (Top Card)
    st.markdown(f"### 📅 Full Session Schedule - {selected_day}")
    st.dataframe(day_df, use_container_width=True)

    st.divider()

    # 4. Substitution Logic
    col_input, col_result = st.columns([1, 2])

    with col_input:
        st.markdown("### 👤 Select Details")
        absent_t = st.selectbox("Absent Teacher:", day_df['Teacher_Name'].unique())
        session_cols = [c for c in day_df.columns if "Session" in c]
        sel_sess = st.selectbox("Required Session:", session_cols)
        
        # Filter available substitutes
        available = []
        for _, row in day_df.iterrows():
            workload = sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))
            if (str(row[sel_sess]).lower() == 'free' and workload < 6 and 
                row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
                available.append(row['Teacher_Name'])

    with col_result:
        st.markdown(f"### 🔍 Proposed Substitutes ({sel_sess})")
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button("🔀 Shuffle"): random.shuffle(available)
        with c1:
            sub_t = st.selectbox("Select Substitute:", available) if available else st.warning("No available substitutes")

        if sub_t and st.button("✅ Confirm & Sync Data"):
            # Update Points Logic (Net Balance)
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
            st.session_state.used_today.append(sub_t)
            
            try:
                conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
                st.success("✅ Google Sheets updated successfully!")
            except:
                st.warning("⚠️ Local update only. (Check Secrets for write access)")
            st.balloons()

    # 5. Net Balance Dashboard (Bottom Card)
    st.divider()
    st.markdown("### 📈 Net Balance Dashboard")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net']
    ), use_container_width=True)

    # Footer Action
    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📤 Download Updated Report", data=csv, file_name=f"AMS_Report_{selected_day}.csv")

except Exception as e:
    st.error(f"Error processing data: {e}")
