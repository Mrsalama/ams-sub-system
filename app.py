import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & UI Professional Style
st.set_page_config(page_title="AMS - ELA Substitution System", layout="wide")

# رابط صورة الخلفية
NEW_BG = "https://img1.wsimg.com/isteam/ip/d03b28ee-bce7-4c2e-abac-d1a2150c0744/AMS%20COVER.jpg/:/cr=t:0%25,l:0%25,w:100%25,h:100%25/rs=w:890,cg:true"

st.markdown(f"""
<style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("{NEW_BG}");
        background-size: cover; background-position: center;
        background-repeat: no-repeat; background-attachment: fixed;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(255, 255, 255, 0.85); z-index: 0;
    }}
    .main .block-container {{ position: relative; z-index: 1; }}
    h1, h2, h3, p, span, label {{ color: #001f3f !important; font-weight: bold !important; }}
    .stDataFrame, div[data-testid="stExpander"] {{
        background-color: white !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15) !important;
    }}
    .session-label {{ color: #000000 !important; font-size: 22px !important; font-weight: 900 !important; display: block; }}
</style>
""", unsafe_allow_html=True)

st.title("🏛️ ELA Department - Smart Substitution System")

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
        # قراءة جدول النقاط فقط
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
    except:
        st.error("Connection Error with Balance Sheet.")
        st.stop()

# 3. Operations Hub
try:
    selected_day = st.sidebar.selectbox("📅 Select Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # قراءة جدول اليوم المحدد بوضوح
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    # التأكد من أننا نستخدم فقط الأعمدة الخاصة باليوم (تجاهل أي أعمدة debit/credit إضافية قد تظهر بالخطأ)
    relevant_columns = [c for c in day_df.columns if "Debit" not in c and "Credit" not in c]
    clean_day_df = day_df[relevant_columns].copy()

    st.subheader("👤 Step 1: Select Absent Teachers")
    all_teachers = clean_day_df['Teacher_Name'].dropna().unique()
    absent_teachers = st.multiselect("Identify teachers who are absent today:", all_teachers)

    if absent_teachers:
        if st.button("🔀 Reshuffle All Substitutes"):
            st.session_state.shuffle_key += 1
            st.rerun()

        st.divider()
        st.subheader("📋 Step 2: Automated Substitution Map")
        
        session_cols = [c for c in clean_day_df.columns if "Session" in c or "P" in c]
        total_assignments = {}
        random.seed(st.session_state.shuffle_key)

        for absent_t in absent_teachers:
            with st.expander(f"📍 Substitution Plan for: {absent_t}", expanded=True):
                absent_row = clean_day_df[clean_day_df['Teacher_Name'] == absent_t].iloc[0]
                busy_sessions = [s for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s])]
                
                cols = st.columns(len(busy_sessions)) if busy_sessions else []
                for i, sess in enumerate(busy_sessions):
                    with cols[i]:
                        possible = []
                        for _, row in clean_day_df.iterrows():
                            t_name = row['Teacher_Name']
                            workload = sum(1 for s in session_cols if str(row[s]).lower() != 'free' and pd.notna(row[s]))
                            
                            # البحث عن رصيد المدرس من جدول الـ Balance المنفصل تماماً
                            bal_row = st.session_state.balance_data[st.session_state.balance_data['Teacher_Name'] == t_name]
                            credit = bal_row['Credit'].values[0] if not bal_row.empty else 0
                            
                            if (t_name not in absent_teachers and str(row[sess]).lower() == 'free' and workload < 6 and credit < 4):
                                possible.append(t_name)
                        
                        chosen_sub = random.choice(possible) if possible else "N/A"
                        st.markdown(f'<span class="session-label">{sess}</span>', unsafe_allow_html=True)
                        final_sub = st.selectbox("Assign Sub:", possible, 
                                                index=possible.index(chosen_sub) if chosen_sub in possible else 0,
                                                key=f"s_{absent_t}_{sess}_{st.session_state.shuffle_key}")
                        total_assignments[f"{absent_t}_{sess}"] = final_sub

        if st.button("🚀 Confirm & Finalize Assignments"):
            # التعديل يتم فقط في الـ balance_data الموجودة في الذاكرة
            for absent_t in absent_teachers:
                absent_row = clean_day_df[clean_day_df['Teacher_Name'] == absent_t].iloc[0]
                count = sum(1 for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s]))
                st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += count
            
            for key, sub_name in total_assignments.items():
                if sub_name != "N/A":
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_name, 'Credit'] += 1
            
            # تحديث شيت الـ Debit & Credit فقط
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("Points Synchronized in Debit & Credit Sheet!")
            st.balloons()

    st.divider()
    st.subheader("📊 Live Performance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#D9534F" if v < 0 else "#22c55e" if v > 0 else "#001f3f"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info(f"Select teachers to start. (Technical Note: {e})")
