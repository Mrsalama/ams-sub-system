import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. إعدادات الصفحة والخلفية
st.set_page_config(page_title="AMS - Smart Substitution System", layout="wide")

# رابط الصورة التي اخترتها
BACKGROUND_IMAGE_URL = "https://get.wallhere.com/photo/school-building-architecture-education-high-school-university-campus-state-school-1383854.jpg"

# كود CSS لضبط الخلفية والتباين (Contrast) والوضوح
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("{BACKGROUND_IMAGE_URL}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}

/* طبقة شبه شفافة لزيادة تباين النصوص (Contrast) لضمان وضوح البيانات */
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(255, 255, 255, 0.88); 
    z-index: 0;
}}

.main .block-container {{
    position: relative;
    z-index: 1;
}}

/* تجميل شكل الجداول */
.stDataFrame {{
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}}
</style>
""", unsafe_allow_html=True)

st.title("🏫 منظومة البدائل الذكية - AMS Integrated System")

# 2. إعدادات الربط بجوجل شيت والـ GIDs
BASE_URL = "https://docs.google.com/spreadsheets/d/1NKg4TUOJCvwdYbak4nTr3JIUoNYE5whHV2LhLaElJYY/edit"
TAB_GIDS = {
    "Sunday": "854353825",
    "Monday": "1006724539",
    "Tuesday": "680211487",
    "Wednesday": "1640660009",
    "Thursday": "1422765568",
    "Debit & Credit": "1340439346"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# 3. إدارة الذاكرة التراكمية (Session State)
if 'balance_data' not in st.session_state:
    try:
        # تحميل سجل الحسابات لأول مرة
        balance_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        balance_df.columns = [str(c).strip() for c in balance_df.columns]
        balance_df['Debit'] = pd.to_numeric(balance_df['Debit'], errors='coerce').fillna(0)
        balance_df['Credit'] = pd.to_numeric(balance_df['Credit'], errors='coerce').fillna(0)
        st.session_state.balance_data = balance_df
    except:
        st.error("تعذر تحميل سجل الحسابات، تأكد من رابط الشيت.")

if 'used_today' not in st.session_state:
    st.session_state.used_today = []

# 4. القائمة الجانبية (Sidebar) لاختيار اليوم والمدرس الغائب
st.sidebar.header("📋 لوحة التحكم")
selected_day = st.sidebar.selectbox("📅 اختر اليوم الدراسي:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])

try:
    # تحميل جدول حصص اليوم المختار
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])
    
    # عرض الجدول الكامل لليوم (ليتمكن المدير من رؤية كل المدرسين)
    st.subheader(f"📊 جدول حصص جميع المدرسين - يوم {selected_day}")
    st.dataframe(day_df, use_container_width=True)
    
    st.divider()

    # 5. منطق اختيار الغائب والبحث عن البديل
    st.sidebar.subheader("👤 تسجيل حالة غياب")
    absent_teacher = st.sidebar.selectbox("اسم المدرس الغائب:", day_df['Teacher_Name'].unique())
    
    # تحديد الحصص المتاحة في الجدول
    session_cols = [c for c in day_df.columns if "Session" in c]
    selected_session = st.sidebar.selectbox("الحصة التي سيغيب فيها:", session_cols)

    # وظيفة لحساب عدد حصص المدرس الفعلية في اليوم (Workload)
    def get_workload(row):
        return sum(1 for c in session_cols if str(row[c]).lower() != 'free' and pd.notna(row[c]))

    # تصفية المدرسين المتاحين للبديلة
    available_subs = []
    for _, row in day_df.iterrows():
        t_name = row['Teacher_Name']
        # الشروط: 
        # 1. يكون "free" في هذه الحصة
        # 2. حصصه الأساسية < 6
        # 3. لم يتم اختياره كبديل اليوم (منع التكرار)
        # 4. ليس هو المدرس الغائب
        if (str(row[selected_session]).lower() == 'free' and 
            get_workload(row) < 6 and 
            t_name not in st.session_state.used_today and 
            t_name != absent_teacher):
            available_subs.append(t_name)

    # عرض واجهة اختيار البديل مع زر Shuffle
    st.subheader(f"🔍 البدلاء المتاحون لحصة {absent_teacher} ({selected_session})")
    
    col_sel, col_shu = st.columns([3, 1])
    
    with col_shu:
        if st.button("🔀 Shuffle"):
            random.shuffle(available_subs)

    with col_sel:
        if available_subs:
            substitute = st.selectbox("اختر المدرس البديل المقترح:", available_subs)
        else:
            st.warning("⚠️ لا يوجد مدرسين متاحين حالياً (الكل مشغول أو وصل لـ 6 حصص).")
            substitute = None

    # 6. زر التأكيد ونظام "المقاصة" (Net Balance)
    if substitute and st.button("✅ Confirm Substitution"):
        # جلب دور الغائب للاستثناء
        role = str(day_df[day_df['Teacher_Name'] == absent_teacher]['Role'].iloc[0])
        is_exempt = "HOD" in role or "Home Class" in role
        
        # تحديث النقاط: الغائب (-1) والبديل (+1)
        if not is_exempt:
            st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_teacher, 'Debit'] += 1
        
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == substitute, 'Credit'] += 1
        
        # إضافة المدرس لقائمة "استخدم اليوم"
        st.session_state.used_today.append(substitute)
        
        st.success(f"تم التسجيل بنجاح! {substitute} دخل بدلاً من {absent_teacher}")
        st.balloons()

    # 7. عرض الميزان التراكمي (Net Balance)
    st.divider()
    st.subheader("📊 الميزان التراكمي (Net Balance)")
    
    # حساب الصافي: Credits - Debits
    # إذا كان غائب مرة (-1) ودخل مكان حد (+1) النتيجة تصبح 0 (اتشالت من عليه)
    res_df = st.session_state.balance_data.copy()
    res_df['Net Balance'] = res_df['Credit'] - res_df['Debit']
    
    # تلوين الأرقام: أحمر للسالب وأخضر للموجب
    def style_net(val):
        color = 'red' if val < 0 else 'green' if val > 0 else 'black'
        return f'color: {color}; font-weight: bold'

    st.dataframe(res_df.style.applymap(style_net, subset=['Net Balance']), use_container_width=True)

    # زر التحميل لتحديث الشيت يدوياً
    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 تحميل التقرير المحدث", data=csv, file_name=f"AMS_Report_{selected_day}.csv")

except Exception as e:
    st.error(f"خطأ في البيانات: {e}")