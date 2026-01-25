import streamlit as st
import pandas as pd
import data_bot  # المحرك

# إعداد الصفحة
st.set_page_config(page_title="منصة البيانات العقارية", layout="wide", page_icon="📊")

# --- التنسيق الجمالي ---
st.markdown("""
<style>
    .big-stat { font-size: 20px; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #ddd; }
    /* تنسيق الجداول */
    .stDataFrame { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- الاتصال بالمحرك ---
if 'bot' not in st.session_state:
    with st.spinner("جاري الاتصال بقاعدة البيانات..."):
        try: st.session_state.bot = data_bot.RealEstateBot()
        except: st.error("خطأ في الاتصال")

df = st.session_state.bot.df if hasattr(st.session_state.bot, 'df') else pd.DataFrame()

# ========================================================
# 🟢 القائمة الجانبية (فلتر البحث)
# ========================================================
with st.sidebar:
    st.title("🔍 فلتر البحث")
    
    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    
    st.divider()

    if df.empty:
        st.warning("جاري سحب البيانات...")
        st.stop()

    # فلتر الحي (اختياري لتسهيل العرض)
    districts = sorted(df['الحي'].unique()) if 'الحي' in df.columns else []
    selected_dist = st.selectbox("تصفية حسب الحي:", ["الكل"] + districts)
    
    # تطبيق الفلتر
    if selected_dist != "الكل":
        filtered_df = df[df['الحي'] == selected_dist]
    else:
        filtered_df = df

    # إحصائيات سريعة في السايدبار
    st.divider()
    st.markdown("### 📊 ملخص البيانات")
    count_sold = len(filtered_df[filtered_df['Data_Category'] == 'صفقات (Sold)'])
    count_ask = len(filtered_df[filtered_df['Data_Category'] == 'عروض (Ask)'])
    st.write(f"🟢 صفقات منفذة: **{count_sold}**")
    st.write(f"🔵 عروض متاحة: **{count_ask}**")

# ========================================================
# 📋 المنطقة الرئيسية (الجدول المطلوب)
# ========================================================
st.title("📊 لوحة البيانات العقارية")
st.caption("استعراض مباشر للبيانات من ملفات جوجل درايف")

# 1. تحديد الأعمدة المطلوبة للعرض (حسب طلبك)
display_columns = [
    'Data_Category', # نوع الملف
    'Source_File',   # اسم الملف
    'الحي',
    'اسم_المطور',     # المطور
    'السعر',
    'المساحة',
    'سعر_المتر',
    'الحالة',
    'نوع_العقار'
]

# إعادة تسمية الأعمدة للعربية في العرض
column_rename_map = {
    'Data_Category': 'نوع الملف (تصنيف)',
    'Source_File': 'اسم الملف المصدري',
    'اسم_المطور': 'المطور',
    'سعر_المتر': 'سعر المتر',
    'نوع_العقار': 'نوع العقار'
}

# 2. إنشاء التبويبات (الخانتين)
tab_deals, tab_offers = st.tabs(["💰 الصفقات (Sold)", "🏷️ العروض (Offers)"])

# --- الخانة الأولى: الصفقات ---
with tab_deals:
    st.subheader("سجل الصفقات المتممة")
    
    # سحب داتا الصفقات فقط
    deals_data = filtered_df[filtered_df['Data_Category'] == 'صفقات (Sold)'].copy()
    
    if not deals_data.empty:
        # التأكد من وجود الأعمدة قبل العرض
        final_cols = [c for c in display_columns if c in deals_data.columns]
        
        # تنسيق الجدول للعرض
        display_df = deals_data[final_cols].rename(columns=column_rename_map)
        
        # عرض الجدول
        st.dataframe(
            display_df.sort_values('سعر المتر'),
            use_container_width=True,
            column_config={
                "السعر": st.column_config.NumberColumn(format="%d ريال"),
                "سعر المتر": st.column_config.NumberColumn(format="%d ريال"),
                "المساحة": st.column_config.NumberColumn(format="%d م²"),
            }
        )
    else:
        st.info("لا توجد صفقات مسجلة في البيانات الحالية.")

# --- الخانة الثانية: العروض ---
with tab_offers:
    st.subheader("قائمة العروض الحالية في السوق")
    
    # سحب داتا العروض فقط
    offers_data = filtered_df[filtered_df['Data_Category'] == 'عروض (Ask)'].copy()
    
    if not offers_data.empty:
        # التأكد من وجود الأعمدة
        final_cols = [c for c in display_columns if c in offers_data.columns]
        
        # تنسيق الجدول
        display_df = offers_data[final_cols].rename(columns=column_rename_map)
        
        # عرض الجدول
        st.dataframe(
            display_df.sort_values('سعر المتر'),
            use_container_width=True,
            column_config={
                "السعر": st.column_config.NumberColumn(format="%d ريال"),
                "سعر المتر": st.column_config.NumberColumn(format="%d ريال"),
                "المساحة": st.column_config.NumberColumn(format="%d م²"),
            }
        )
    else:
        st.warning("لا توجد عروض متاحة حالياً.")
