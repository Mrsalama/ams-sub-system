import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. إعدادات الصفحة والستايل لتحسين الوضوح (Contrast)
st.set_page_config(page_title="AMS - Substitution System", layout="wide")

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("https://i.ibb.co/v4m3S3v/rs-w-890-cg-true.webp");
    background-size: cover; background-position: center; background-attachment: fixed;
}}
[data-testid="stAppViewContainer"]::before {{
    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.9); z-index: 0;
}}
h1, h2, h3, p, span, label {{
    color: #000000 !important; font-weight: bold !important;
}}
.stDataFrame {{
    background-color: white !important; border-radius: 10px; padding: 5px;
}}
</style>
""", unsafe_allow_html=True)

st.title("🏫 منظومة البدائل الذكية - AMS")

# 2. الربط بجوجل شيت
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825", "Monday": "1006724539", "Tuesday": "680211487",
    "Wednesday": "1640660009", "Thursday": "1422765568", "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- الخطوة الحاسمة: تهيئة كل المتغيرات (Initialization) ---
if 'balance_data' not in st.session_state:
    try:
        # محاولة قراءة سجل الحسابات
        df_bal = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        df_bal.columns = [str(c).strip() for c in df_bal.columns]
        df_bal['Debit'] = pd.to_numeric(df_bal['Debit'], errors='coerce').fillna(0)
        df_bal['Credit'] = pd.to_numeric(df_bal['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = df_bal
    except Exception as e:
        st.error(f"⚠️ فشل في تحميل سجل الحسابات. يرجى التحقق من إعدادات الـ Secrets. الخطأ: {e}")
        st.stop() # إيقاف التنفيذ هنا حتى يتم حل المشكلة

if 'used_today' not in st.session_state:
    st.session_state.used_today = []

# 3. محرك النظام (يظهر فقط إذا تم التحميل بنجاح)
try:
    selected_day = st.sidebar.selectbox("📅 اختر اليوم الدراسي:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    
    # تحميل جدول حصص اليوم
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])
    
    st.subheader(f"📊 جدول الحصص الكامل - {selected_day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("👤 المدرس الغائب:", day_df['Teacher_Name'].unique())
    session_cols = [c for c in day_df.columns if "Session" in c]
    sel_sess = st.sidebar.selectbox("⏳ الحصة المطلوبة:", session_cols)

    # فلترة البدلاء المتاحين
    available = []
    for _, row in day_df.iterrows():
        workload = sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))
        if (str(row[sel_sess]).lower() == 'free' and workload < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 البدلاء المتاحون (الحصة: {sel_sess})")
    c_sel, c_shu = st.columns([3, 1])
    with c_shu: 
        if st.button("🔀 Shuffle"): random.shuffle(available)
    with c_sel:
        sub_t = st.selectbox("المدرس المقترح:", available) if available else st.warning("لا يوجد بديل متاح")

    # 4. زر التأكيد ونظام "المقاصة" (Net Balance)
    if sub_t and st.button("✅ تأكيد ومزامنة البيانات"):
        # تحديث الميزان: الغائب (+1 Debit) والبديل (+1 Credit)
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        
        # إضافة البديل لقائمة المستخدمين اليوم لمنع تكراره
        st.session_state.used_today.append(sub_t)
        
        # محاولة تحديث جوجل شيت أونلاين
        try:
            conn.update(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}", data=st.session_state.balance_data)
            st.success("✅ تم تحديث جوجل شيت بنجاح!")
        except:
            st.warning("⚠️ التحديث تم داخلياً فقط. تأكد من إعدادات الـ Secrets للكتابة في الشيت.")
        st.balloons()

    # 5. عرض الميزان الصافي فقط
    st.divider()
    st.subheader("📊 ميزان النقاط التراكمي (Net Balance)")
    final_df = st.session_state.balance_data.copy()
    final_df['Net'] = final_df['Credit'] - final_df['Debit']
    
    st.dataframe(final_df[['Teacher_Name', 'Debit', 'Credit', 'Net']].style.applymap(
        lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net']
    ), use_container_width=True)

except Exception as e:
    st.error(f"حدث خطأ في معالجة البيانات: {e}")
