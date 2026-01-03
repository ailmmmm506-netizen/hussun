import streamlit as st
import numpy as np
import pandas as pd
import time

# --- إعداد الصفحة ---
st.set_page_config(page_title="المطور العقاري - النسخة الاحترافية", layout="wide", page_icon="🏢")

# --- التنسيق (CSS) ---
st.markdown("""
<style>
    .big-font {font-size:20px !important; font-weight: bold;}
    .success-box {padding: 20px; background-color: #d4edda; border-radius: 10px; border: 1px solid #c3e6cb; color: #155724;}
    .warning-box {padding: 20px; background-color: #fff3cd; border-radius: 10px; border: 1px solid #ffeeba; color: #856404;}
</style>
""", unsafe_allow_html=True)

# --- كلاس التحليل ---
class FeasibilityEngine:
    def __init__(self, area, price, const_cost, margin, floors, efficiency):
        self.area = area
        self.price = price
        self.const_cost = const_cost
        self.target_margin = margin / 100
        self.floors = floors
        self.efficiency = efficiency / 100

    def calculate(self, avg_market_land=None, avg_sell_price=None):
        # إذا لم يدخل المستخدم أسعار سوق، نستخدم المحاكاة
        if avg_market_land is None:
            avg_market_land = self.price * np.random.uniform(0.95, 1.05)
        
        if avg_sell_price is None:
            # معادلة تقريبية: سعر البيع = (سعر الأرض/الكفاءة) + البناء + 30% ربح مطور
            avg_sell_price = (avg_market_land / 2.0) + self.const_cost + 1500

        # الحسابات الأساسية
        total_land_cost = self.area * self.price
        total_bua = self.area * self.floors # إجمالي مسطحات البناء
        net_sellable = total_bua * self.efficiency # الصافي للبيع
        
        total_const_cost = total_bua * self.const_cost
        soft_costs = (total_land_cost + total_const_cost) * 0.12 # 12% مصاريف إدارية وتسويق
        
        total_project_cost = total_land_cost + total_const_cost + soft_costs
        expected_revenue = net_sellable * avg_sell_price
        
        net_profit = expected_revenue - total_project_cost
        roi = (net_profit / total_project_cost) * 100
        
        # السعر العادل للأرض لتحقيق الهامش المطلوب
        # Revenue / (1+Margin) = Max Total Cost
        # Max Land Cost = Max Total Cost - Const - Soft
        max_total_cost = expected_revenue / (1 + self.target_margin)
        # تقريب المصاريف الإدارية كنسبة
        fair_land_total = (max_total_cost - total_const_cost) / 1.12
        fair_land_price_per_m = fair_land_total / self.area

        return {
            "market_land_avg": avg_market_land,
            "market_sell_avg": avg_sell_price,
            "total_dev_cost": total_project_cost,
            "revenue": expected_revenue,
            "profit": net_profit,
            "roi": roi,
            "fair_price": fair_land_price_per_m,
            "bua": total_bua,
            "sellable": net_sellable
        }

# --- الواجهة (UI) ---
st.title("🏢 نظام دراسة الجدوى العقارية المتكامل")
st.markdown("---")

# تقسيم الشاشة إلى تبويبات
tab1, tab2, tab3 = st.tabs(["📝 المدخلات", "📊 التحليل والنتائج", "📑 التقرير النهائي"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. بيانات الأرض والموقع")
        location = st.text_input("اسم الحي / المدينة", "الرياض - حي النرجس")
        area = st.number_input("مساحة الأرض (م2)", 800, step=50)
        price = st.number_input("سعر المتر المعروض (ريال)", 3500, step=100)
        floors = st.number_input("عدد الأدوار المسموحة (نظام البناء)", 3.0, step=0.5)
        
    with col2:
        st.subheader("2. فرضيات التطوير")
        const_cost = st.number_input("تكلفة البناء المباشرة (ريال/م2)", 2000, help="عظم + تشطيب + إشراف")
        efficiency = st.slider("كفاءة المساحة البيعية %", 70, 95, 80, help="كم نسبة الصافي من الإجمالي؟")
        margin = st.slider("هامش الربح المستهدف %", 15, 50, 25)

    st.markdown("---")
    st.subheader("3. بيانات السوق (اختياري)")
    st.info("💡 إذا كنت تعرف أسعار السوق الحقيقية أدخلها هنا، وإلا اتركها فارغة ليقوم النظام بتقديرها.")
    use_manual_data = st.checkbox("إدخال أسعار السوق يدوياً")
    
    manual_land_avg = None
    manual_sell_avg = None
    
    if use_manual_data:
        c1, c2 = st.columns(2)
        manual_land_avg = c1.number_input("متوسط سعر أراضي الحي (ريال/م)", value=3500)
        manual_sell_avg = c2.number_input("متوسط سعر بيع الشقق الجديد (ريال/م)", value=6500)

    analyze_btn = st.button("🚀 بدء دراسة الجدوى", type="primary", use_container_width=True)

# تشغيل التحليل
if analyze_btn:
    engine = FeasibilityEngine(area, price, const_cost, margin, floors, efficiency)
    results = engine.calculate(manual_land_avg, manual_sell_avg)
    
    # تخزين النتائج في Session State لنقلها بين التبويبات
    st.session_state['results'] = results
    st.session_state['inputs'] = {'loc': location, 'area': area, 'price': price}
    st.success("تم التحليل بنجاح! انتقل لتبويب 'التحليل والنتائج' لرؤية التفاصيل.")

# تبويب النتائج
with tab2:
    if 'results' in st.session_state:
        res = st.session_state['results']
        
        # مؤشرات الأداء الرئيسية (KPIs)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("صافي الربح المتوقع", f"{res['profit']:,.0f} ريال")
        kpi2.metric("العائد على الاستثمار ROI", f"{res['roi']:.2f}%", delta_color="normal" if res['roi'] >= margin else "inverse")
        kpi3.metric("السعر العادل للأرض", f"{res['fair_price']:,.0f} ريال", delta=f"{res['fair_price'] - price:.0f}")
        kpi4.metric("إيرادات المشروع", f"{res['revenue']:,.0f} ريال")
        
        st.markdown("---")
        
        # الرسم البياني
        chart_col1, chart_col2 = st.columns([2, 1])
        with chart_col1:
            st.subheader("توزيع التكاليف والأرباح")
            chart_data = pd.DataFrame({
                "البند": ["ثمن الأرض", "تكلفة البناء", "مصاريف إدارية", "صافي الربح"],
                "القيمة": [
                    area * price, 
                    res['total_dev_cost'] - (area*price) - (res['total_dev_cost']*0.12/1.12), # تقريبي للعرض
                    res['total_dev_cost'] * 0.12, # تقريبي
                    res['profit']
                ]
            })
            st.bar_chart(chart_data.set_index("البند"))
            
        with chart_col2:
            st.subheader("التوصية الذكية")
            if res['roi'] >= margin:
                st.markdown(f"""<div class="success-box">
                ✅ <b>فرصة استثمارية مميزة</b><br>
                المشروع يحقق عائداً يتجاوز طموحك ({margin}%).<br>
                السعر المعروض للأرض يعتبر لقطة.
                </div>""", unsafe_allow_html=True)
            elif res['roi'] > 0:
                 st.markdown(f"""<div class="warning-box">
                ⚠️ <b>فرصة مشروطة</b><br>
                المشروع رابح لكنه لم يحقق الهدف ({margin}%).<br>
                يجب التفاوض لتنزيل سعر الأرض إلى <b>{res['fair_price']:,.0f} ريال</b>.
                </div>""", unsafe_allow_html=True)
            else:
                st.error("⛔ المشروع خاسر بالسعر الحالي. لا ينصح بالشراء.")

# تبويب التقرير
with tab3:
    if 'results' in st.session_state:
        res = st.session_state['results']
        inp = st.session_state['inputs']
        
        st.header("📑 ملخص دراسة الجدوى")
        st.text(f"تاريخ التقرير: {time.strftime('%Y-%m-%d')}")
        st.text(f"الموقع: {inp['loc']}")
        
        report_df = pd.DataFrame({
            "البيان": ["مساحة الأرض", "سعر المتر (أرض)", "مسطحات البناء (BUA)", "المساحة البيعية الصافية", "إجمالي التكلفة", "الإيراد المتوقع", "صافي الربح", "العائد ROI"],
            "القيمة": [
                f"{inp['area']} م2",
                f"{inp['price']} ريال",
                f"{res['bua']:,.0f} م2",
                f"{res['sellable']:,.0f} م2",
                f"{res['total_dev_cost']:,.0f} ريال",
                f"{res['revenue']:,.0f} ريال",
                f"{res['profit']:,.0f} ريال",
                f"{res['roi']:.2f} %"
            ]
        })
        st.table(report_df)
        
        # زر تحميل البيانات (CSV)
        csv = report_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 تحميل الملخص (CSV)",
            data=csv,
            file_name="feasibility_study.csv",
            mime="text/csv",
        )
    else:
        st.info("قم بإجراء التحليل أولاً لعرض التقرير.")
