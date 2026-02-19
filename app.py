import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Config & Modern UI Styling
st.set_page_config(page_title="AMS - Modern Substitution", layout="wide")

st.markdown(f"""
<style>
/* Modern Gradient Background */
[data-testid="stAppViewContainer"] {{
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    background-attachment: fixed;
}}

/* Glassmorphism Effect for Containers */
.stDataFrame, .sub-box, div[data-testid="stMetricContainer"] {{
    background: rgba(255, 255, 255, 0.9) !important;
    border-radius: 15px !important;
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1) !important;
    backdrop-filter: blur(4px);
}}

/* Typography */
h1, h2, h3, p, label {{
    color: #1e3a8a !important;
    font-family: 'Inter', sans-serif;
    font-weight: 700 !important;
}}

/* Custom Styled Buttons */
.stButton>button {{
    background: #2563eb !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    border: none !important;
    transition: all 0.3s ease;
}}

.stButton>button:hover {{
    background: #1d4ed8 !important;
    transform: translateY(-2px);
}}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Modern Substitution Hub - Al-Alamia")

# 2. Connection
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}
conn = st.connection("gsheets", type=GSheetsConnection)

# Data Init
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
        st.error("Connection lost. Check Cloud Secrets.")
        st.stop()

# 3. Main Logic
try:
    selected_day = st.sidebar.selectbox("📅 Select Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    # --- Modern Selection: Clickable Teacher List ---
    st.subheader("👤 Select Absent Teacher")
    teacher_list = day_df['Teacher_Name'].dropna().unique()
    
    # عرض المدرسين كأزرار أنيقة (Click to select)
    cols_t = st.columns(5)
    absent_t = st.session_state.get('selected_absent', None)

    for idx, t_name in enumerate(teacher_list):
        with cols_t[idx % 5]:
            if st.button(t_name, key=f"btn_{t_name}", use_container_width=True):
                st.session_state.selected_absent = t_name
                st.rerun()

    if absent_t:
        st.info(f"Selected Absent Teacher: **{absent_t}**")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
        busy_sessions = [s for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s])]

        # Substitution Display
        st.markdown("### 🔄 Automated Substitution Plan")
        plan_cols = st.columns(len(busy_sessions)) if busy_sessions else []
        current_plan = {}

        for i, sess in enumerate(busy_sessions):
            with plan_cols[i]:
                # Logic for finding subs
                possible = []
                for _, row in day_df.iterrows():
                    workload = sum(1 for s in session_cols if str(row[s]).lower() != 'free' and pd.notna(row[s]))
                    credit = st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == row['Teacher_Name'], 'Credit'].values[0]
                    if row['Teacher_Name'] != absent_t and str(row[sess]).lower() == 'free' and workload < 6 and credit < 4:
                        possible.append(row['Teacher_Name'])
                
                if sess not in st.session_state.locked_subs or st.session_state.locked_subs[sess] not in possible:
                    st.session_state.locked_subs[sess] = random.choice(possible) if possible else "N/A"
                
                st.markdown(f"**{sess}**")
                is_kept = st.checkbox("Keep", key=f"lock_{sess}")
                st.success(st.session_state.locked_subs[sess])
                current_plan[sess] = st.session_state.locked_subs[sess]

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔀 Reshuffle Unlocked"):
                for s in busy_sessions:
                    if not st.session_state.get(f"lock_{s}"):
                        st.session_state.locked_subs.pop(s, None)
                st.rerun()
        with c2:
            if st.button("🚀 Confirm & Sync to Cloud"):
                st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += len(busy_sessions)
                for s, sub in current_plan.items():
                    if sub != "N/A":
                        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub, 'Credit'] += 1
                conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
                st.balloons()
                st.success("Cloud Data Updated!")

    # --- Full Teachers Schedule (As requested) ---
    st.divider()
    st.subheader("📅 Full Teachers' Schedule View")
    st.dataframe(day_df, use_container_width=True)

    # --- Performance Ledger ---
    st.subheader("📊 Points Ledger (Debit/Credit)")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#ef4444" if v < 0 else "#22c55e" if v > 0 else "#1e3a8a"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Choose a teacher from the list to start the substitution process.")
