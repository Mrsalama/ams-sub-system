import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. إعدادات الصفحة والخلفية
st.set_page_config(page_title="AMS - Smart Substitution System", layout="wide")

BACKGROUND_IMAGE = "https://get.wallhere.com/photo/school-building-architecture-education-high-school-university-campus-state-school-1383854.jpg"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("{BACKGROUND_IMAGE}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.88); 
    z-index: 0;
}}
.main .block-container {{ position: relative; z-index: 1; }}
</style>
""", unsafe_allow_html=True)

st.title("🏫 منظومة البدائل الذكية - AMS")

# 2. الربط بجوجل شيت
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

# إنشاء الاتصال
conn = st.connection("gsheets", type=GSheetsConnection)

# --- الخطوة الأهم: تهيئة البيانات (Initialization) ---
if 'balance_data' not in st.session_state:
    try:
        # محاولة تحميل سجل الحسابات
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal.columns = [str(c).strip() for c in df_bal.columns]
        
        # تحويل البيانات لأرقام
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        
        st.session_state.balance_data = df_bal
        st.session_state.used_today = []
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال بجوجل شيت. تأكد من إعدادات الـ Secrets. الخطأ: {e}")
        st.stop() # إيقاف التطبيق هنا حتى يتم حل مشكلة الاتصال

# 3. واجهة المستخدم (تظهر فقط إذا نجح الاتصال)
try:
    selected_day = st.sidebar.selectbox("📅 اختر اليوم الدراسي:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # تحميل جدول اليوم
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])

    st.subheader(f"📊 جدول الحصص الكامل - {selected_day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("👤 المدرس الغائب:", day_df['Teacher_Name'].unique())
    sessions = [c for c in day_df.columns if "Session" in c]
    sel_session = st.sidebar.selectbox("⏳ الحصة المطلوبة:", sessions)

    # فلترة البدلاء
    def workload(row):
        return sum(1 for c in sessions if str(row[c]).lower() != 'free' and pd.notna(row[c]))

    available = []
    for _, row in day_df.iterrows():
        if (str(row[sel_session]).lower() == 'free' and workload(row) < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 البدلاء المتاحون (الحصة: {sel_session})")
    col_sel, col_shu = st.columns([3, 1])
    with col_shu: 
        if st.button("🔀 Shuffle"): random.shuffle(available)
    
    with col_sel:
        sub_t = st.selectbox("المدرس المقترح:", available) if available else st.warning("لا يوجد بدلاء متاحين")

    if sub_t and st.button("✅ Confirm Substitution"):
        # تحديث الحسابات
        role = str(day_df[day_df['Teacher_Name'] == absent_t]['Role'].iloc[0])
        if "HOD" not in role and "Home Class" not in role:
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        st.session_state.used_today.append(sub_t)
        
        # محاولة تحديث الشيت أونلاين فوراً
        try:
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("✅ تم التحديث في جوجل شيت بنجاح!")
        except:
            st.warning("⚠️ تم التحديث داخلياً فقط (مشكلة في صلاحيات الكتابة)، يرجى تحميل الملف يدوياً.")
            
        st.balloons()

    st.divider()
    st.subheader("📊 ميزان النقاط (Net Balance)")
    res_df = st.session_state.balance_data.copy()
    res_df['Net'] = res_df['Credit'] - res_df['Debit']
    
    st.dataframe(res_df.style.applymap(lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net']), use_container_width=True)

    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 تحميل التقرير المحدث", data=csv, file_name=f"AMS_Update.csv")

except Exception as e:
    st.error(f"خطأ في معالجة البيانات: {e}")
