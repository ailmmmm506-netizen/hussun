import streamlit as st
import pandas as pd
import data_bot
import importlib

# 1. إعداد الصفحة
st.set_page_config(page_title="المحلل العقاري الذكي", layout="wide", page_icon="🏢")

# 2. القائمة الجانبية
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث البيانات", use_container_width=True, type="primary"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        importlib.reload(data_bot)
        st.rerun()

st.title("🧐 مدقق البيانات العقارية: تحليل السوق")

# 3. تشغيل الروبوت
if 'bot' not in st.session_state:
    with st.spinner("جاري سحب وتحليل البيانات..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except Exception as e:
            st.error(f"حدث خطأ أثناء التشغيل: {e}")

# 4. عرض البيانات
if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات. تأكد من الملفات في جوجل درايف.")
    else:
        # --- الفلاتر ---
        st.markdown("### 🧹 فلترة البيانات")
        col_clean1, col_clean2 = st.columns(2)
        with col_clean1:
            min_price = st.number_input("استبعد الصفقات أقل من (سعر المتر):", value=500, step=100)
        with col_clean2:
            max_price = st.number_input("استبعد الصفقات أعلى من (سعر المتر):", value=20000, step=1000)

        clean_df = df[(df['سعر_المتر'] >= min_price) & (df['سعر_المتر'] <= max_price)].copy()
        
        # --- البحث ---
        st.divider()
        st.markdown("### 🔍 تحليل الحي")
        col1, col2 = st.columns([3, 1])
        with col1:
            search_text = st.text_input("اسم الحي:", "الملقا")
        with col2:
            st.write("##")
            btn = st.button("عرض التقرير 📊", use_container_width=True, type="primary")

        if btn or search_text:
            mask = clean_df['الحي'].astype(str).str.contains(search_text, na=False)
            results = clean_df[mask].copy()
            
            if results.empty:
                st.info(f"لم نجد بيانات لحي '{search_text}' ضمن الحدود السعرية.")
            else:
                # العدادات
                land_df = results[results['نوع_العقار'].str.contains('أرض', na=False)]
                build_df = results[results['نوع_العقار'].str.contains('مبني', na=False)]
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("عدد الأراضي", f"{len(land_df):,}")
                m2.metric("متوسط متر الأرض", f"{land_df['سعر_المتر'].median():,.0f} ريال")
                m3.metric("عدد المباني", f"{len(build_df):,}")
                m4.metric("متوسط متر المبنى", f"{build_df['سعر_المتر'].median():,.0f} ريال")
                
                st.write("---")
                
                # الجدول
                view_cols = ['الحي', 'نوع_العقار', 'المساحة', 'السعر', 'سعر_المتر', 'اسم_المطور', 'Source_Type']
                final_cols = [c for c in view_cols if c in results.columns]
                
                st.dataframe(
                    results[final_cols].style.format({
                        'السعر': '{:,.0f}',
                        'المساحة': '{:,.2f}',
                        'سعر_المتر': '{:,.0f}'
                    }),
                    use_container_width=True
                )
