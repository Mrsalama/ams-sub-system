import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & Professional Blue & White Style
st.set_page_config(page_title="AMS - Smart Substitution", layout="wide")

st.markdown(f"""
<style>
/* Background and Overlay */
[data-testid="stAppViewContainer"] {{
    background-image: url("https://i.ibb.co/v4m3S3v/rs-w-890-cg-true.webp");
    background-size: contain; background-position: center; background-repeat: no-repeat; background-attachment: fixed;
    background-color: #F0F2F6;
}}
[data-testid="stAppViewContainer"]::before {{
    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.9); z-index: 0;
}}
.main .block-container {{ position: relative; z-index: 1; }}

/* Typography - Royal Blue & Black */
h1, h2, h3, p, span, label {{ color: #1E3A8A !important; font-weight: bold; font-family: 'Inter', sans-serif; }}

/* Cards Styling */
.sub-box {{
    background-color: #FFFFFF; border: 2px solid #DBEAFE; border-radius: 12px;
    padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(30, 58, 138, 0.1);
}}

/* Sidebar & Buttons */
[data-testid="stSidebar"] {{ background-color: #FFFFFF !important; border-right: 2px solid #DBEAFE; }}
.stButton>button {{
    background: #1E3A8A !important; color: white !important;
    border-radius: 8px !important; width: 100%; border: none !important;
}}
div.stButton > button:first-child {{ background: #2563EB !important; }} /* Primary Blue */
</style>
""", unsafe_allow_html=True)

st.title("🏛️ ELA Teachers' Smart Substitution")

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
    except:
        st.error("Connection Error.")
        st.stop()

# Persistent storage for selected subs during shuffle
if 'locked_subs' not in st.session_state:
    st.session_state.locked_subs = {}

# 3. Automation Logic
try:
    selected_day = st.sidebar.selectbox("Select Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    teachers = [""] + list(day_df['Teacher_Name'].dropna().unique())
    absent_t = st.sidebar.selectbox("Select Absent Teacher:", teachers)

    if absent_t:
        st.subheader(f"📋 Suggested Plan for {absent_t}")
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
        busy_sessions = [s for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s])]

        def get_possible_subs(sess_name):
            possible = []
            for _, row in day_df.iterrows():
                workload = sum(1 for s in session_cols if str(row[s]).lower() != 'free' and pd.notna(row[s]))
                current_credit = st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == row['Teacher_Name'], 'Credit'].values[0]
                if (row['Teacher_Name'] != absent_t and str(row[sess_name]).lower() == 'free' and workload < 6 and current_credit < 4):
                    possible.append(row['Teacher_Name'])
            return possible

        # Substitution Display Grid
        cols = st.columns(len(busy_sessions)) if busy_sessions else []
        current_plan = {}

        for i, sess in enumerate(busy_sessions):
            with cols[i]:
                possible_list = get_possible_subs(sess)
                
                # Logic for locking/shuffling
                if sess not in st.session_state.locked_subs or st.session_state.locked_subs[sess] not in possible_list:
                    chosen = random.choice(possible_list) if possible_list else "None"
                    st.session_state.locked_subs[sess] = chosen
                
                st.markdown(f'<div class="sub-box"><small>{sess}</small></div>', unsafe_allow_html=True)
                
                # The "Selection" mechanism: Select if suitable
                is_suitable = st.checkbox("Keep", key=f"check_{sess}", value=False)
                
                # Display the teacher name
                st.write(f"**{st.session_state.locked_subs[sess]}**")
                current_plan[sess] = st.session_state.locked_subs[sess]

        st.sidebar.divider()
        if st.sidebar.button("🔀 Shuffle Unlocked"):
            # Clear only unlocked ones
            for s in busy_sessions:
                if not st.session_state.get(f"check_{s}"):
                    st.session_state.locked_subs.pop(s, None)
            st.rerun()

        if st.button("✅ Confirm & Submit to Cloud"):
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += len(busy_sessions)
            for s, teacher in current_plan.items():
                if teacher != "None":
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == teacher, 'Credit'] += 1
            
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("Synchronized Successfully!")
            st.balloons()

    # Ledger (The Table)
    st.divider()
    st.subheader("📊 Performance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#DC2626" if v < 0 else "#16A34A" if v > 0 else "#1E3A8A"}', subset=['Net']
    ), use_container_width=True)

    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Export CSV", csv, f"AMS_Report.csv", "text/csv")

except Exception as e:
    st.info("Select a teacher from the sidebar to start.")
