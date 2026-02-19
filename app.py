import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration
st.set_page_config(page_title="AMS - Auto Substitution", layout="wide")

# School Style CSS
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("https://images.unsplash.com/photo-1541339907198-e08756ebafe3?q=80&w=2070&auto=format&fit=crop");
    background-size: cover; background-attachment: fixed;
}}
[data-testid="stAppViewContainer"]::before {{
    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(245, 247, 249, 0.92); z-index: 0;
}}
.main .block-container {{ position: relative; z-index: 1; }}
h1, h2, h3, p, span, label {{ color: #1A365D !important; font-weight: bold; }}
.sub-box {{
    background-color: #ffffff; border: 2px solid #E2E8F0; border-radius: 12px;
    padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ ELA Teachers' Automated Substitution")

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

if 'used_in_session' not in st.session_state:
    st.session_state.used_in_session = []

# 3. Main Logic
try:
    selected_day = st.sidebar.selectbox("Select Day:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    # قائمة المدرسين تبدأ بخيار فارغ كما طلبت
    teachers = [""] + list(day_df['Teacher_Name'].dropna().unique())
    absent_t = st.sidebar.selectbox("Select Absent Teacher:", teachers)

    if absent_t != "":
        st.subheader(f"📋 Substitution Plan for {absent_t}")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
        # الحصص التي لا تحتوي على كلمة Free
        busy_sessions = [s for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s])]

        # زر الـ Shuffle
        if st.button("🔀 Reshuffle All Substitutes"):
            st.rerun()

        final_assignments = {}
        cols = st.columns(len(busy_sessions)) if busy_sessions else st.info("No busy sessions found.")

        for i, sess in enumerate(busy_sessions):
            with cols[i]:
                # منطق اختيار البديل الذكي:
                possible = []
                for _, row in day_df.iterrows():
                    # حساب النصاب اليومي
                    workload = sum(1 for s in session_cols if str(row[s]).lower() != 'free' and pd.notna(row[s]))
                    # رصيد البدائل الحالي
                    current_credit = st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == row['Teacher_Name'], 'Credit'].values[0]
                    
                    if (row['Teacher_Name'] != absent_t and 
                        str(row[sess]).lower() == 'free' and 
                        workload < 6 and 
                        current_credit < 4):
                        possible.append(row['Teacher_Name'])
                
                chosen_sub = random.choice(possible) if possible else "No Sub Available"
                final_assignments[sess] = chosen_sub
                
                st.markdown(f"""<div class="sub-box">
                    <small style="color:gray">{sess}</small><br>
                    <span style="font-size:18px">{chosen_sub}</span>
                </div>""", unsafe_allow_html=True)

        if st.button("✅ Confirm & Submit to Cloud"):
            # تحديث الخصم للغائب
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += len(busy_sessions)
            # تحديث الرصيد للبدلاء
            for s, teacher in final_assignments.items():
                if teacher != "No Sub Available":
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == teacher, 'Credit'] += 1
            
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("Synchronized Successfully!")
            st.balloons()

    # Ledger
    st.divider()
    st.subheader("📊 Performance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Please select a teacher from the sidebar to generate the plan.")
