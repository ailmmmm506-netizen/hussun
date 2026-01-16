import streamlit as st
import pandas as pd
import data_bot
import importlib

# إعداد الصفحة
st.set_page_config(page_title="مدقق البيانات العقارية", layout="wide", page_icon="🧐")

# القائمة الجانبية
with st.sidebar:
    st.header("⚙️ التحكم")
    if st.button("🔄 تحديث البيانات", type="primary", use_container_width=True):
        st.cache_data.clear()
        for key in list(st.session_state.keys()): del st.session_state[key]
        importlib.reload(data_bot)
        st.rerun()

st.title("🧐 مدقق البيانات العقارية: تنظيف وتحليل")

# تشغيل الروبوت
if 'bot' not in st.session_state:
    with st.spinner("جاري سحب البيانات الخام..."):
        try:
            st.session_state.bot = data_bot.RealEstateBot()
        except Exception as e:
            st.error(f"خطأ: {e}")

if 'bot' in st.session_state and hasattr(st.session_state.bot, 'df'):
    df = st.session_state.bot.df
    
    if df.empty:
        st.warning("⚠️ لا توجد بيانات.")
    else:
        # ---------------------------------------------------------
        # 1. منطقة التنظيف (Cleaning Zone) - أهم جزء للدراسة
        # ---------------------------------------------------------
        st.markdown("### 🧹 1. تنظيف البيانات (استبعاد الشوائب)")
        
        col_clean1, col_clean2, col_clean3 = st.columns(3)
        
        with col_clean1:
            # فلتر استبعاد الصفقات الرخيصة جداً (الإرث والهبات)
            min_price = st.number_input("⛔ استبعد الصفقات التي سعر المتر أقل من:", value=500, step=100, help="يستبعد الصفقات غير التجارية مثل الهبات")
        
        with col_clean2:
            # فلتر استبعاد الصفقات الغالية جداً (أخطاء الإدخال)
            max_price = st.number_input("⛔ استبعد الصفقات التي سعر المتر أعلى من:", value=20000, step=1000)

        # تطبيق الفلترة
        clean_df = df[(df['سعر_المتر'] >= min_price) & (df['سعر_المتر'] <= max_price)].copy()
        
        removed_count = len(df) - len(clean_df)
        if removed_count > 0:
            st.warning(f"⚠️ تم استبعاد {removed_count} صفقة تعتبر 'شاذة' بناءً على الفلاتر أعلاه.")
        
        st.markdown("---")

        # ---------------------------------------------------------
        # 2. البحث والتحليل (على البيانات النظيفة)
        # ---------------------------------------------------------
        st.markdown("### 🔍 2. تحليل الحي (بيانات نظيفة)")
        
        col_search1, col_search2 = st.columns([3, 1])
        with col_search1:
            search_text = st.text_input("اسم الحي:", "الملقا")
        with col_search2:
            st.write("##")
            btn = st.button("تحليل الحي 📊", use_container_width=True, type="primary")

        if btn or search_text:
            # البحث في البيانات النظيفة فقط
            mask = clean_df['الحي'].astype(str).str.contains(search_text, na=False)
            results = clean_df[mask].copy()
            
            if results.empty:
                st.info(f"لا توجد بيانات لحي {search_text} ضمن الحدود السعرية المختارة.")
            else:
                # عرض الملخص
                land_df = results[results['نوع_العقار'].str.contains('أرض', na=False)]
                build_df = results[results['نوع_العقار'].str.contains('مبني', na=False)]
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("عدد الأراضي", f"{len(land_df):,}")
                m2.metric("متوسط متر الأرض", f"{land_df['سعر_المتر'].median():,.0f} ريال")
                m3.metric("عدد المباني", f"{len(build_df):,}")
                m4.metric("متوسط متر المبنى", f"{build_df['سعر_المتر'].median():,.0f} ريال")
                
                # ---------------------------------------------------------
                # 3. جدول التدقيق (الشفافية الكاملة)
                # ---------------------------------------------------------
                st.markdown("#### 🕵️‍♂️ جدول التدقيق: قارن حكم الروبوت بالواقع")
                st.write("هنا يمكنك رؤية كيف صنف الروبوت العقار، ومقارنته بالسعر والمساحة لتقرر بنفسك.")
                
                # عرض أعمدة محددة للمقارنة
                view_cols = ['الحي', 'نوع_العقار', 'نوع_العقار_الخام', 'المساحة', 'السعر', 'سعر_المتر', 'Source_File']
                # التأكد من وجود الأعمدة
                final_cols = [c for c in view_cols if c in results.columns]
                
                st.dataframe(
                    results[final_cols].style.format({
                        'السعر': '{:,.0f}',
                        'المساحة': '{:,.2f}',
                        'سعر_المتر': '{:,.0f}'
                    }).applymap(lambda x: 'background-color: #d4edda' if 'أرض' in str(x) else '', subset=['نوع_العقار']),
                    use_container_width=True,
                    height=600
                )