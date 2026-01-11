import streamlit as st
import pandas as pd
from data_bot import RealEstateBot

# 1. إعداد الصفحة
st.set_page_config(page_title="المحلل العقاري الذكي", page_icon="🏗️", layout="centered")

# تنسيق CSS بسيط لجعل الجدول يظهر بشكل عربي جميل
st.markdown("""
<style>
    thead tr th {text-align: right !important;}
    tbody tr td {text-align: right !important;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
</style>
""", unsafe_allow_html=True)

# 2. العنوان
st.title("📊 داشبورد تحليل الأسعار (متصل بدرايف)")
st.caption("يتم سحب البيانات مباشرة من مجلدك في Google Drive")
st.markdown("---")

# 3. تشغيل الروبوت (مرة واحدة فقط لتسريع الأداء)
if 'bot' not in st.session_state:
    with st.spinner('🔄 جاري الاتصال بملفاتك في Google Drive...'):
        st.session_state.bot = RealEstateBot()
    
    if not st.session_state.bot.df.empty:
        st.toast(f"✅ تم تحميل {len(st.session_state.bot.df)} صفقة بنجاح!", icon="🎉")
    else:
        st.error("⚠️ لم يتم العثور على بيانات في المجلد.")

# 4. واجهة الإدخال
col_input, col_btn = st.columns([3, 1])
with col_input:
    district = st.text_input("اكتب اسم الحي:", placeholder="مثال: العارض")
with col_btn:
    st.write("##") # مسافة لضبط الزر
    analyze_btn = st.button("🔍 تحليل", use_container_width=True)

# 5. عرض النتائج
if analyze_btn and district:
    # استدعاء دالة التحليل من الروبوت
    result = st.session_state.bot.fetch_data(district)
    
    if result["status"] == "success":
        st.header(f"نتائج تحليل: حي {district}")
        
        # أ. عرض الأرقام الكبيرة (الملخص)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("سعر متر الأرض (تطوير)", f"{result['summary']['exec_avg']:,} ريال")
        with c2:
            st.metric("سعر متر الشقة (بيع)", f"{result['summary']['built_avg']:,} ريال")
        with c3:
            st.metric("سعر الوحدة المقترح", f"{result['summary']['ticket_cap']:,} ريال")
        
        st.markdown("---")
        
        # ب. الجدول التفصيلي (وهذا اللي طلبته: يوضح المصدر قدام كل معلومة)
        st.subheader("📋 تفاصيل البيانات والمصادر")
        
        # تحويل البيانات لجدول عرض
        df_display = pd.DataFrame(result["records"])
        
        # عرض الجدول بشكل نظيف
        st.table(df_display)
        
        # رسالة توضيحية عن المصدر العام
        st.info(f"💡 ملاحظة: {result['msg']}")

        # ج. روابط للتحقق اليدوي
        links = st.session_state.bot.generate_links("الرياض", district)
        st.markdown("### 🔗 روابط خارجية للتحقق")
        col_link1, col_link2 = st.columns(2)
        with col_link1:
            st.link_button("تطبيق عقار (العروض الحالية)", links['aqar'])
        with col_link2:
            st.link_button("البورصة العقارية (الصفقات)", links['srem'])
            
    else:
        st.warning("⚠️ لم نجد بيانات دقيقة لهذا الحي في ملفاتك، جرب اسماً آخر.")

# تذييل الصفحة
st.markdown("---")
st.markdown("Developed by **Real Estate Bot** v2.0 🤖")
