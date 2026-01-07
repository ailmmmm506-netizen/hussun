import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="المطور العقاري الذكي | v7.0",
    layout="wide",
    page_icon="🏗️",
    initial_sidebar_state="expanded"
)

# --- تنسيق CSS ---
st.markdown("""
<style>
    .main {background-color: #fcfcfc;}
    .stMetric {background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px;}
    .cost-box {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #90caf9;
        color: #0d47a1;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- دوال مساعدة ---
def parse_maps_link(link):
    """محاولة استخراج الإحداثيات من رابط قوقل ماب"""
    if not link:
        return None, None
    # البحث عن نمط الإحداثيات @lat,lon
    match = re.search(r'@([-.\d]+),([-.\d]+)', link)
    if match:
        return float(match.group(1)), float(match.group(2))
    # البحث عن نمط q=lat,lon
    match_q = re.search(r'q=([-.\d]+),([-.\d]+)', link)
    if match_q:
        return float(match_q.group(1)), float(match_q.group(2))
    return None, None

# --- المحرك الحسابي ---
class MasterEngine:
    def __init__(self, inputs):
        self.inputs = inputs

    def run_analysis(self):
        # 1. الحسابات الأساسية
        land_cost = self.inputs['area'] * self.inputs['land_price']
        total_bua = self.inputs['area'] * self.inputs['floors']
        net_sellable = total_bua * (self.inputs['efficiency'] / 100)
        
        const_cost_total = total_bua * self.inputs['const_cost']
        soft_costs = (land_cost + const_cost_total) * (self.inputs['soft_pct'] / 100)
        
        total_dev_cost = land_cost + const_cost_total + soft_costs
        total_revenue = net_sellable * self.inputs['sell_price']
        
        net_profit = total_revenue - total_dev_cost
        roi = (net_profit / total_dev_cost) * 100
        
        # سعر التعادل (كم كلفني المتر الصافي؟)
        breakeven_price = total_dev_cost / net_sellable if net_sellable > 0 else 0
        
        # السعر العادل للأرض
        fair_land_price = ((total_revenue / (1 + self.inputs['target_margin']/100)) - const_cost_total) / (1 + self.inputs['soft_pct']/100) / self.inputs['area']

        # 2. التدفقات النقدية
        duration = self.inputs['duration']
        timeline = range(duration + 1)
        cash_flow = np.zeros(duration + 1)
        
        # دفعة الأرض والمصاريف
        cash_flow[0] = -(land_cost + soft_costs * 0.2)
        
        build_months = max(1, duration - 2)
        monthly_const = (const_cost_total + soft_costs * 0.8) / build_months
        for m in range(1, build_months + 1):
            cash_flow[m] -= monthly_const
            
        start_sales = int(duration * 0.5)
        sales_months = duration - start_sales + 1
        monthly_rev = total_revenue / sales_months
        
        for m in range(start_sales, duration + 1):
            if m <= duration:
                cash_flow[m] += monthly_rev
        
        cumulative_cash = np.cumsum(cash_flow)
        
        df_cash = pd.DataFrame({
            "الشهر": timeline,
            "صافي التدفق": cash_flow,
            "السيولة التراكمية": cumulative_cash
        })

        return {
            "kpis": {
                "profit": net_profit,
                "roi": roi,
                "revenue": total_revenue,
                "total_cost": total_dev_cost,
                "fair_land": fair_land_price,
                "peak_cash": abs(min(cumulative_cash)),
                "breakeven": breakeven_price
            },
            "cash_flow": df_cash,
            "net_sellable": net_sellable
        }

    def sensitivity_matrix(self, base_roi):
        sell_vars = [-10, -5, 0, 5, 10]
        const_vars = [-10, -5, 0, 5, 10]
        matrix = []
        for s in sell_vars:
            row = []
            for c in const_vars:
                # محاكاة سريعة
                new_rev = self.run_analysis()['kpis']['revenue'] * (1 + s/100)
                base_const = self.inputs['area'] * self.inputs['floors'] * self.inputs['const_cost']
                new_const = base_const * (1 + c/100)
                land = self.inputs['area'] * self.inputs['land_price']
                soft = (land + new_const) * (self.inputs['soft_pct']/100)
                new_total_cost = land + new_const + soft
                new_roi = ((new_rev - new_total_cost) / new_total_cost) * 100
                row.append(new_roi)
            matrix.append(row)
        return pd.DataFrame(matrix, index=[f"بيع {x}%" for x in sell_vars], columns=[f"بناء {x}%" for x in const_vars])

# --- القائمة الجانبية (Inputs) ---
with st.sidebar:
    st.title("🏗️ إعدادات المشروع")
    
    # 1. الموقع والرابط
    st.subheader("1. الموقع")
    city = st.text_input("المدينة", "الرياض")
    map_link = st.text_input("رابط الموقع (Google Maps)", placeholder="انسخ الرابط هنا...")
    
    # محاولة استخراج الإحداثيات تلقائياً
    default_lat, default_lon = 24.7136, 46.6753
    if map_link:
        extracted_lat, extracted_lon = parse_maps_link(map_link)
        if extracted_lat:
            default_lat, default_lon = extracted_lat, extracted_lon
            st.success("تم تحديد الموقع من الرابط بنجاح! ✅")
    
    # إحداثيات مخفية داخل Expander لمن يريد التعديل اليدوي
    with st.expander("تعديل الإحداثيات يدوياً"):
        lat = st.number_input("Lat", value=default_lat, format="%.6f")
        lon = st.number_input("Lon", value=default_lon, format="%.6f")

    # 2. الأرض
    st.subheader("2. تفاصيل الأرض")
    area = st.number_input("المساحة (م2)", 200, 50000, 900)
    street_width = st.number_input("عرض الشارع (م)", 10, 100, 20)
    land_price = st.number_input("سعر متر الأرض (ريال)", 500, 50000, 3200)

    # 3. التطوير (مع الحساب الفوري)
    st.subheader("3. تكاليف التطوير")
    floors = st.number_input("عدد الأدوار", 1.0, 50.0, 4.0)
    const_cost = st.number_input("تكلفة البناء (ريال/م2)", 800, 10000, 2100)
    soft_pct = st.slider("مصاريف إدارية وتطوير %", 1, 30, 12)
    
    # --- الميزة الجديدة: الحساب المباشر للتكلفة ---
    # حساب سريع للعرض فقط
    _total_bua = area * floors
    _land_cost = area * land_price
    _const_cost = _total_bua * const_cost
    _soft = (_land_cost + _const_cost) * (soft_pct/100)
    _total_project_cost = _land_cost + _const_cost + _soft
    
    # تكلفة المتر المطور (على مساحة الأرض)
    _cost_per_land_m = _total_project_cost / area
    # تكلفة المتر البيعي (على المساحة البيعية - افتراض كفاءة 80% مبدئياً للعرض)
    _est_sellable = _total_bua * 0.80
    _breakeven = _total_project_cost / _est_sellable
    
    st.markdown(f"""
    <div class="cost-box">
    ت. المتر المطور (على الأرض): {_cost_per_land_m:,.0f} ريال<br>
    ت. المتر البيعي (عليك): {_breakeven:,.0f} ريال
    </div>
    """, unsafe_allow_html=True)
    # ---------------------------------------------

    duration = st.slider("مدة المشروع (شهر)", 6, 60, 18)

    # 4. المبيعات
    st.subheader("4. المبيعات")
    efficiency = st.slider("كفاءة المساحة البيعية %", 50, 95, 80)
    sell_price = st.number_input("سعر بيع المتر (ريال)", 1000, 100000, 6800)
    target_margin = st.slider("هامش الربح المستهدف %", 10, 100, 25)

    btn = st.button("🚀 تشغيل التحليل", type="primary")

# --- الواجهة الرئيسية ---
st.title(f"دراسة جدوى: {city}")
if map_link:
    st.caption(f"🔗 رابط الموقع: {map_link}")

if btn:
    inputs = {
        "area": area, "land_price": land_price, "floors": floors, 
        "const_cost": const_cost, "soft_pct": soft_pct, "duration": duration,
        "efficiency": efficiency, "sell_price": sell_price, "target_margin": target_margin,
        "street_width": street_width, "map_link": map_link, "city": city
    }
    
    engine = MasterEngine(inputs)
    results = engine.run_analysis()
    kpis = results['kpis']

    # التبويبات
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 اللوحة الرئيسية", 
        "💰 التدفقات النقدية", 
        "🎲 المخاطر", 
        "📝 عرض المستثمر",
        "📥 التصدير"
    ])

    # Tab 1: Dashboard
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("صافي الربح", f"{kpis['profit']:,.0f} ﷼")
        c2.metric("العائد ROI", f"{kpis['roi']:.2f}%", delta_color="normal" if kpis['roi']>=target_margin else "inverse")
        c3.metric("نقطة التعادل (للمتر)", f"{kpis['breakeven']:,.0f} ﷼", help="أقل سعر بيع لتغطية التكاليف دون ربح")
        c4.metric("السعر العادل للأرض", f"{kpis['fair_land']:,.0f} ﷼", delta=f"{kpis['fair_land']-land_price:.0f}")
        
        st.markdown("---")
        
        mc1, mc2 = st.columns([1, 1])
        with mc1:
            st.subheader("📍 الموقع على الخريطة")
            st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=13)
        
        with mc2:
            st.subheader("تحليل التكلفة الإجمالية")
            cost_df = pd.DataFrame({
                "البند": ["قيمة الأرض", "تكلفة البناء", "مصاريف إدارية", "الربح"],
                "القيمة": [
                    area*land_price,
                    (area*floors*const_cost),
                    kpis['total_cost'] - (area*land_price) - (area*floors*const_cost),
                    kpis['profit']
                ]
            })
            st.bar_chart(cost_df.set_index("البند"))

    # Tab 2: Cash Flow
    with tab2:
        st.subheader("تحليل السيولة (J-Curve)")
        st.line_chart(results['cash_flow'].set_index("الشهر")['السيولة التراكمية'])
        st.dataframe(results['cash_flow'].style.format("{:,.0f}"))

    # Tab 3: Sensitivity
    with tab3:
        st.subheader("تحليل الحساسية (المخاطر)")
        sens_df = engine.sensitivity_matrix(kpis['roi'])
        fig, ax = plt.subplots()
        im = ax.imshow(sens_df.values, cmap="RdYlGn", vmin=0, vmax=40)
        ax.set_xticks(np.arange(len(sens_df.columns)))
        ax.set_yticks(np.arange(len(sens_df.index)))
        ax.set_xticklabels(sens_df.columns)
        ax.set_yticklabels(sens_df.index)
        for i in range(len(sens_df.index)):
            for j in range(len(sens_df.columns)):
                text = ax.text(j, i, f"{sens_df.values[i, j]:.1f}%",
                               ha="center", va="center", color="black", fontweight="bold")
        st.pyplot(fig)

    # Tab 4: Pitch
    with tab4:
        st.subheader("رسالة العرض الاستثماري")
        pitch = f"""
        **فرصة تطوير عقاري في {city}**
        
        الموقع: {map_link if map_link else "لم يحدد"}
        المساحة: {area}م2 على شارع {street_width}م.
        
        **دراسة الجدوى المختصرة:**
        نتوقع تطوير مبنى سكني بتكلفة إجمالية {kpis['total_cost']/1000000:.2f} مليون ريال.
        متوسط تكلفة المتر البيعي علينا (نقطة التعادل): {kpis['breakeven']:,.0f} ريال.
        
        سعر البيع المقترح: {sell_price} ريال/م.
        صافي الربح المتوقع: {kpis['profit']/1000000:.2f} مليون ريال ({kpis['roi']:.2f}% عائد).
        """
        st.text_area("نسخ النص:", pitch, height=250)

    # Tab 5: Export
    with tab5:
        st.subheader("تصدير البيانات")
        report_data = {
            "البيان": ["المدينة", "رابط الموقع", "المساحة", "سعر الأرض", "تكلفة المتر (بناء)", "سعر البيع", "نقطة التعادل", "الربح", "ROI"],
            "القيمة": [city, map_link, area, land_price, const_cost, sell_price, kpis['breakeven'], kpis['profit'], kpis['roi']]
        }
        df_rep = pd.DataFrame(report_data)
        st.dataframe(df_rep)
        csv = df_rep.to_csv(index=False).encode('utf-8')
        st.download_button("📥 تحميل CSV", data=csv, file_name="feasibility_v7.csv", mime="text/csv")

else:
    st.info("👈 أدخل رابط الموقع والبيانات لبدء التحليل.")
