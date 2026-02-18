import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. إعدادات الصفحة والخلفية (التباين المحسن)
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
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(255, 255, 255, 0.92); 
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

conn = st.connection("gsheets", type=GSheetsConnection)

# --- معالجة ذكية لتبويب الحسابات ---
if 'balance_data' not in st.session_state:
    try:
        # قراءة الشيت بالكامل
        raw_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS['Debit & Credit']}")
        
        # البحث عن الصف الذي يحتوي على كلمة Teacher_Name
        # إذا لم يجدها، سيفترض أن البيانات تبدأ من أول صف غير فارغ
        raw_df = raw_df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        
        # محاولة تعيين أسماء الأعمدة الصحيحة
        if "Teacher_Name" not in raw_df.columns:
            # إذا كانت البيانات في أول صف، اجعله هيدر
            new_header = raw_df.iloc[0] 
            raw_df = raw_df[1:]
            raw_df.columns = new_header
            
        # تنظيف نهائي لأسماء الأعمدة
        raw_df.columns = [str(c).strip() for c in raw_df.columns]
        
        # التأكد من وجود الأعمدة أو تسميتها بالترتيب (مدرس، غياب، دخول)
        target_cols = ['Teacher_Name', 'Debit', 'Credit']
        if not all(col in raw_df.columns for col in target_cols):
             raw_df.columns = target_cols + list(raw_df.columns[len(target_cols):])

        # تحويل القيم لأرقام لضمان عمل المقاصة (+1 و -1)
        raw_df['Debit'] = pd.to_numeric(raw_df['Debit'], errors='coerce').fillna(0)
        raw_df['Credit'] = pd.to_numeric(raw_df['Credit'], errors='coerce').fillna(0)
        
        st.session_state.balance_data = raw_df
        st.session_state.used_today = []
    except Exception as e:
        st.error(f"⚠️ فشل في تنظيم أعمدة الحسابات. يرجى التأكد من تبويب Debit & Credit. الخطأ: {e}")
        st.stop()

# 3. محرك النظام (الجداول والبدائل)
try:
    selected_day = st.sidebar.selectbox("📅 اختر اليوم الدراسي:", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
    day_df = conn.read(spreadsheet=f"{BASE_URL}#gid={TAB_GIDS[selected_day]}", header=1)
    day_df.columns = [str(c).strip() for c in day_df.columns]
    day_df = day_df.dropna(subset=['Teacher_Name'])

    st.subheader(f"📊 جدول الحصص - {selected_day}")
    st.dataframe(day_df, use_container_width=True)

    st.sidebar.divider()
    absent_t = st.sidebar.selectbox("👤 المدرس الغائب:", day_df['Teacher_Name'].unique())
    sessions = [c for c in day_df.columns if "Session" in c]
    sel_session = st.sidebar.selectbox("⏳ الحصة المطلوبة:", sessions)

    # حساب نصاب المدرس (يجب أن يكون أقل من 6 حصص)
    def check_workload(row):
        return sum(1 for c in sessions if str(row[c]).lower() != 'free' and pd.notna(row[c]))

    available = []
    for _, row in day_df.iterrows():
        if (str(row[sel_session]).lower() == 'free' and check_workload(row) < 6 and 
            row['Teacher_Name'] not in st.session_state.used_today and row['Teacher_Name'] != absent_t):
            available.append(row['Teacher_Name'])

    st.subheader(f"🔍 البدلاء المتاحون لحصة {absent_t}")
    col_sel, col_shu = st.columns([3, 1])
    with col_shu: 
        if st.button("🔀 Shuffle"): random.shuffle(available)
    
    with col_sel:
        sub_t = st.selectbox("المدرس البديل المقترح:", available) if available else st.warning("لا يوجد بديل متاح")

    if sub_t and st.button("✅ تأكيد البديلة والمقاصة"):
        # تسجيل النقاط: الغائب +1 في Debit (خصم)، البديل +1 في Credit (إضافة)
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == absent_t, 'Debit'] += 1
        st.session_state.balance_data.loc[st.session_state.balance_data['Teacher_Name'] == sub_t, 'Credit'] += 1
        st.session_state.used_today.append(sub_t)
        st.success(f"تمت العملية! رصيد {sub_t} تحسن بمقدار نقطة.")
        st.balloons()

    # 4. عرض الميزان الصافي (Net Balance)
    st.divider()
    st.subheader("📊 ميزان النقاط التراكمي (Net Balance)")
    res_df = st.session_state.balance_data.copy()
    res_df['Net Balance'] = res_df['Credit'] - res_df['Debit']
    
    # تلوين السالب بالأحمر والموجب بالأخضر
    st.dataframe(res_df.style.applymap(lambda v: f'color: {"red" if v < 0 else "green" if v > 0 else "black"}', subset=['Net Balance']), use_container_width=True)

except Exception as e:
    st.error(f"حدث خطأ في النظام: {e}")
