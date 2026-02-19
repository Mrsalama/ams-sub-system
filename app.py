import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Page Configuration & UI
st.set_page_config(page_title="AMS - ELA Substitution System", layout="wide")

st.markdown(f"""
<style>
    [data-testid="stAppViewContainer"] {{ background-color: #F7F9FC; }}
    h1, h2, h3 {{ color: #004A99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 600 !important; }}
    .stDataFrame, .sub-box, div[data-baseweb="select"], .stAlert {{
        background-color: #FFFFFF !important; border-radius: 10px !important;
        border: 1px solid #E1E4E8 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }}
    .stButton>button {{
        background: linear-gradient(180deg, #0056B3 0%, #004A99 100%) !important;
        color: white !important; border: none !important; border-radius: 6px !important;
    }}
</style>
""", unsafe_allow_html=True)

st.title("👨‍🏫 ELA Teachers' Automated Substitution")

# 2. Connection Logic
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize Session States
if 'shuffle_key' not in st.session_state:
    st.session_state.shuffle_key = 0

if 'balance_data' not in st.session_state:
    try:
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal = df_bal.dropna(how='all', axis=0).dropna(how='all', axis=1)
        df_bal.columns = ['Teacher_Name', 'Debit', 'Credit'] + list(df_bal.columns[3:])
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

# 3. Main Operations
try:
    selected_day = st.sidebar.selectbox("📅 Select Day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    
    st.subheader("👤 Select Absent Teachers")
    all_teachers = day_df['Teacher_Name'].dropna().unique()
    absent_teachers = st.multiselect("Identify teachers who are absent today:", all_teachers)

    if absent_teachers:
        # زر الـ Shuffle الآن يقوم بتغيير مفتاح عشوائي لإجبار الصفحة على التحديث
        if st.button("🔀 Reshuffle All Substitutes"):
            st.session_state.shuffle_key += 1
            st.rerun()

        st.divider()
        st.markdown("### 🔄 Live Substitution Plan")
        
        session_cols = [c for c in day_df.columns if "Session" in c or "P" in c]
        total_assignments = {}
        
        # استخدام الـ shuffle_key لضمان تغيير النتائج عند كل ضغطة
        random.seed(st.session_state.shuffle_key)

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
                    
                    # اختيار مدرس بديل عشوائي
                    chosen_sub = random.choice(possible) if possible else "N/A"
                    
                    st.markdown(f"<small style='color:#004A99'>{sess}</small>", unsafe_allow_html=True)
                    # استبدال selectbox بـ text_input أو عرض مباشر لضمان عمل الـ Shuffle
                    final_sub = st.selectbox("Assign:", possible, 
                                            index=possible.index(chosen_sub) if chosen_sub in possible else 0,
                                            key=f"sel_{absent_t}_{sess}_{st.session_state.shuffle_key}")
                    
                    total_assignments[f"{absent_t}_{sess}"] = final_sub

        if st.button("🚀 Confirm & Finalize Assignments"):
            for absent_t in absent_teachers:
                absent_row = day_df[day_df['Teacher_Name'] == absent_t].iloc[0]
                session_count = sum(1 for s in session_cols if str(absent_row[s]).lower() != 'free' and pd.notna(absent_row[s]))
                st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += session_count
            
            for key, sub_name in total_assignments.items():
                if sub_name != "N/A":
                    st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_name, 'Credit'] += 1
            
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("Synchronized successfully!")
            st.balloons()

    st.divider()
    st.subheader("📊 Performance Ledger")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    st.dataframe(res_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"#D9534F" if v < 0 else "#5CB85C" if v > 0 else "#004A99"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.info("Select teachers to start.")
