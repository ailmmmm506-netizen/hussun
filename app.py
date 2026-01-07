import streamlit as st
import numpy as np
import pandas as pd
import time

# --- إعداد الصفحة (Page Config) ---
st.set_page_config(
    page_title="المطور العقاري برو | Real Estate Pro",
    layout="wide",
    page_icon="🏙️",
    initial_sidebar_state="expanded"
)

# --- التنسيق المخصص (CSS Styling) ---
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
    .big-font {font-size:18px !important; color: #333;}
    .header-style {color: #1f77b4;}
</style>
""", unsafe_allow_html=True)

# --- المحرك الحسابي (Calculation Engine) ---
class FeasibilityEngine:
    def __init__(self, area, price, const_cost, margin, floors, efficiency):
        self.area = area
        self.price = price
        self.const_cost = const_cost
        self.target_margin = margin / 100
        self.floors = floors
        self.efficiency = efficiency / 100

    def calculate(self, avg_market_land=None, avg_sell_price=None):
        # محاكاة البيانات في حال عدم الإدخال اليدوي
        if avg_market_land is None:
            avg_market_land = self.price * np.random.uniform(0.95, 1.05)
        
        if avg_sell_price is None:
            # معادلة تقديرية: (سعر الأرض/2) + تكلفة البناء + 2500 هامش وتسويق
            avg_sell_price = (avg_market_land / 2.0) + self.const_cost + 2500

        # الحسابات الأساسية
        total_land_cost = self.area * self.price
        total_bua = self.area * self.floors
        net_sellable = total_bua * self.efficiency
        
        total_const_cost = total_bua * self.const_cost
        # المصاريف الإدارية والتسويقية (Soft Costs)
        soft_costs = (total_land_cost + total_const_cost) * 0.12 
        
        total_project_cost = total_land_cost + total_const_cost + soft_costs
        expected_revenue = net_sellable * avg_sell_price
        
        net_profit = expected_revenue - total_project_cost
        roi = (net_profit / total_project_cost) * 100
        
        # السعر العادل (Reverse Calculation)
        max_total_cost = expected_revenue / (1 + self.target_margin)
        fair_land_total = (max_total_cost - total_const_cost) / 1.12
        fair_land_price_per_m = fair_land_total / self.area

        return {
            "inputs": {"area": self.area, "price": self.price, "floors": self.floors},
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

    # ميزة جديدة: تحليل الحساسية
    def sensitivity_analysis(self, base_results):
        scenarios = []
        # نقوم بتغيير تكلفة البناء وسعر البيع بنسبة -10% و +10%
        variations = [-0.10, 0.0, 0.10] 
        
        base_sell_price = base_results['market_sell_avg']
        base_const_cost = self.const_cost
        
        for v_sell in variations:
            row = []
            for v_const in variations:
                # محاكاة سيناريو جديد
                new_sell = base_sell_price * (1 + v_sell)
                new_const = base_const_cost * (1 + v_const)
                
                # إعادة الحساب سريعاً
                t_land = self.area * self.price
                t_bua = self.area * self.floors
                t_const = t_bua * new_const
                t_soft = (t_land + t_const) * 0.12
                t_total = t_land + t_const + t_soft
                revenue = (t_bua * self.efficiency) * new_sell
                profit = revenue - t_total
                roi = (profit / t_total) * 100
                
                row.append(roi)
            scenarios.append(row)
            
        return pd.DataFrame(scenarios, 
                            index=["نزول السوق 10%", "سعر ثابت", "ارتفاع السوق 10%"],
                            columns=["توفير بناء 10%", "تكلفة بناء ثابتة", "زيادة تكلفة 10%"])

# --- القائمة الجانبية (Sidebar) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1019/1019709.png", width=80)
    st.title("المطور العقاري")
    st.markdown("نسخة: v3.0 (Pro)")
    st.markdown("---")
    
    st.header("1. بيانات الأرض")
    location = st.text_input("📍 اسم الحي / المدينة", "الرياض - الملقا")
    area = st.number_input("مساحة الأرض (م2)", value=800, step=50)
    price = st.number_input("سعر المتر (ريال)", value=3800, step=100)
    floors = st.number_input("عدد الأدوار", value=3.5, step=0.5)
    
    st.header("2. التكاليف والبيع")
    const_cost = st.number_input("تكلفة البناء (ريال/م2)", value=2100)
    margin = st.slider("الربح المستهدف %", 15, 50, 25)
    
    st.markdown("---")
    analyze_btn = st.button("🚀 تحليل الفرصة الآن", type="primary")

# --- الواجهة الرئيسية ---
st.title(f"دراسة جدوى: {location}")

if analyze_btn:
    # 1. التشغيل
    with st.spinner("جاري تحليل البيانات وحساب السيناريوهات..."):
        time.sleep(1)
        engine = FeasibilityEngine(area, price, const_cost, margin, floors, 80)
        res = engine.calculate()
        sensitivity_df = engine.sensitivity_analysis(res)
    
    # 2. عرض النتائج العلوية
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("صافي الربح", f"{res['profit']:,.0f} ﷼")
    col2.metric("العائد ROI", f"{res['roi']:.2f}%", delta_color="normal" if res['roi']>=margin else "inverse")
    col3.metric("السعر العادل للأرض", f"{res['fair_price']:,.0f} ﷼", delta=f"{res['fair_price']-price:.0f}")
    col4.metric("إجمالي الإيراد", f"{res['revenue']:,.0f} ﷼")
    
    st.markdown("---")

    # 3. التبويبات التفصيلية
    tab1, tab2, tab3 = st.tabs(["📊 التحليل المالي", "🎲 تحليل المخاطر (الحساسية)", "📝 عرض المستثمر"])
    
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("توزيع رأس المال")
            df_chart = pd.DataFrame({
                "البند": ["قيمة الأرض", "البناء والتطوير", "مصاريف إدارية وتسويق", "صافي الربح"],
                "القيمة": [
                    area*price, 
                    res['total_dev_cost'] - (area*price) - (res['total_dev_cost']*0.12/1.12),
                    res['total_dev_cost'] * 0.12,
                    res['profit']
                ]
            })
            st.bar_chart(df_chart.set_index("البند"))
        with c2:
            st.info(f"""
            **مؤشرات المشروع:**
            * مسطحات البناء: {res['bua']:,.0f} م2
            * المساحة البيعية: {res['sellable']:,.0f} م2
            * متوسط سعر بيع المتر المتوقع: {res['market_sell_avg']:,.0f} ريال
            """)

    with tab2:
        st.subheader("تحليل ماذا لو؟ (Sensitivity Analysis)")
        st.caption("هذا الجدول يوضح نسبة العائد (ROI) في حال تغيرت تكاليف البناء أو أسعار البيع.")
        
        # تنسيق الجدول بالألوان
        st.dataframe(sensitivity_df.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=30).format("{:.1f}%"))
        
        st.write("📌 **كيف تقرأ الجدول؟** اللون الأخضر يعني أمان عالي، الأحمر يعني خسارة محتملة.")

    with tab3:
        st.subheader("مسودة عرض للمستثمرين (Auto-Generated Pitch)")
        pitch_text = f"""
        **فرصة استثمارية في {location}**
        
        نعرض عليكم فرصة لتطوير أرض سكنية بمساحة {area} متر مربع.
        المشروع يهدف لإنشاء مبنى سكني مكون من {floors} أدوار، بمساحة بيعية إجمالية تبلغ {res['sellable']:,.0f} متر.
        
        **المؤشرات المالية:**
        بناءً على دراسة السوق الحالية، نتوقع تحقيق إيرادات إجمالية قدرها {res['revenue']/1000000:.2f} مليون ريال، 
        وصافي ربح يقدر بـ {res['profit']/1000000:.2f} مليون ريال، مما يحقق عائداً على الاستثمار يبلغ {res['roi']:.2f}% خلال مدة التطوير.
        
        سعر الأرض الحالي ({price} ريال/م) يعتبر {("جيداً" if res['roi'] >= 20 else "مرتفعاً قليلاً")} مقارنة بأسعار المنطقة.
        """
        st.text_area("انسخ النص التالي:", pitch_text, height=250)

else:
    st.info("👈 أدخل البيانات في القائمة اليمنى واضغط زر التحليل")
    
    # خريطة توضيحية (Placeholder)
    st.caption("موقع افتراضي (الرياض)")
    st.map(pd.DataFrame({'lat': [24.7136], 'lon': [46.6753]}))
