import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="المطور العقاري الشامل | Master Developer",
    layout="wide",
    page_icon="🏙️",
    initial_sidebar_state="expanded"
)

# --- تنسيق CSS لتحسين المظهر ---
st.markdown("""
<style>
    .main {background-color: #fcfcfc;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
    .success-text {color: #28a745; font-weight: bold;}
    .danger-text {color: #dc3545; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- المحرك الحسابي الشامل ---
class MasterEngine:
    def __init__(self, inputs):
        self.inputs = inputs

    def run_analysis(self):
        # 1. الحسابات الأساسية (Static)
        land_cost = self.inputs['area'] * self.inputs['land_price']
        total_bua = self.inputs['area'] * self.inputs['floors']
        net_sellable = total_bua * (self.inputs['efficiency'] / 100)
        
        const_cost_total = total_bua * self.inputs['const_cost']
        soft_costs = (land_cost + const_cost_total) * (self.inputs['soft_pct'] / 100)
        
        total_dev_cost = land_cost + const_cost_total + soft_costs
        total_revenue = net_sellable * self.inputs['sell_price']
        
        net_profit = total_revenue - total_dev_cost
        roi = (net_profit / total_dev_cost) * 100
        
        # السعر العادل (Back Calculation)
        # Revenue = (Land + Const + Soft) * (1 + Margin)
        # Land = (Revenue / (1+Margin)) - Const - Soft (Soft contains Land%, so simplified here)
        fair_land_price = ((total_revenue / (1 + self.inputs['target_margin']/100)) - const_cost_total) / (1 + self.inputs['soft_pct']/100) / self.inputs['area']

        # 2. التدفقات النقدية (Time Series)
        duration = self.inputs['duration']
        timeline = range(duration + 1)
        cash_flow = np.zeros(duration + 1)
        
        # المصروفات (Outflows)
        # الشهر 0: الأرض + جزء من المصاريف
        cash_flow[0] = -(land_cost + soft_costs * 0.2)
        
        # البناء (موزع على الأشهر)
        build_months = max(1, duration - 2) # نفترض الانتهاء قبل شهرين للتسليم
        monthly_const = (const_cost_total + soft_costs * 0.8) / build_months
        for m in range(1, build_months + 1):
            cash_flow[m] -= monthly_const
            
        # الإيرادات (Inflows)
        # نفترض البيع يبدأ في النصف الثاني من المشروع
        start_sales = int(duration * 0.5)
        sales_months = duration - start_sales + 1 # +1 يمتد لما بعد التسليم بشهر افتراضاً
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
                "peak_cash": abs(min(cumulative_cash))
            },
            "cash_flow": df_cash,
            "net_sellable": net_sellable
        }

    def sensitivity_matrix(self, base_roi):
        # مصفوفة الحساسية (تغير سعر البيع vs تغير تكلفة البناء)
        sell_vars = [-10, -5, 0, 5, 10]
        const_vars = [-10, -5, 0, 5, 10]
        
        matrix = []
        for s in sell_vars:
            row = []
            for c in const_vars:
                # حسبة سريعة لل ROI الجديد
                new_rev = self.run_analysis()['kpis']['revenue'] * (1 + s/100)
                # تكلفة البناء فقط هي التي تتغير
                base_const = self.inputs['area'] * self.inputs['floors'] * self.inputs['const_cost']
                new_const = base_const * (1 + c/100)
                
                # نعيد حساب التكلفة الكلية (الأرض ثابتة)
                land = self.inputs['area'] * self.inputs['land_price']
                soft = (land + new_const) * (self.inputs['soft_pct']/100)
                new_total_cost = land + new_const + soft
                
                new_roi = ((new_rev - new_total_cost) / new_total_cost) * 100
                row.append(new_roi)
            matrix.append(row)
            
        return pd.DataFrame(matrix, index=[f"بيع {x}%" for x in sell_vars], columns=[f"بناء {x}%" for x in const_vars])

# --- الواجهة: القائمة الجانبية (Inputs) ---
with st.sidebar:
    st.title("🏗️ إعدادات المشروع")
    
    st.subheader("1. الموقع والبيانات الأساسية")
    # تحديث: إضافة الحي والمدينة وعرض الشارع
    city = st.text_input("المدينة", "الرياض")
    district = st.text_input("الحي", "حي العارض")
    street_width = st.number_input("عرض الشارع (م)", 10, 100, 20, help="عرض الشارع قد يؤثر على نظام البناء وقيمة الأرض")
    
    col_coords1, col_coords2 = st.columns(2)
    with col_coords1:
        lat = st.number_input("خط العرض", 24.00, 26.00, 24.8607)
    with col_coords2:
        lon = st.number_input("خط الطول", 46.00, 48.00, 46.6167)

    st.subheader("2. تفاصيل الأرض")
    area = st.number_input("المساحة (م2)", 200, 50000, 900)
    land_price = st.number_input("سعر المتر (ريال)", 500, 50000, 3200)

    st.subheader("3. التطوير")
    floors = st.number_input("عدد الأدوار", 1.0, 50.0, 4.0)
    const_cost = st.number_input("تكلفة البناء (ريال/م2)", 800, 10000, 2100)
    soft_pct = st.slider("مصاريف إدارية %", 1, 30, 12)
    duration = st.slider("مدة المشروع (شهر)", 6, 60, 18)

    st.subheader("4. المبيعات والأهداف")
    efficiency = st.slider("كفاءة المساحة البيعية %", 50, 95, 80)
    sell_price = st.number_input("سعر بيع المتر (ريال)", 1000, 100000, 6800)
    target_margin = st.slider("هامش الربح المستهدف %", 10, 100, 25)

    btn = st.button("🚀 تشغيل التحليل الشامل", type="primary")

# --- الواجهة الرئيسية ---
st.title(f"دراسة جدوى عقارية: {city} - {district}")
st.caption(f"على شارع عرض {street_width}م")

if btn:
    inputs = {
        "area": area, "land_price": land_price, "floors": floors, 
        "const_cost": const_cost, "soft_pct": soft_pct, "duration": duration,
        "efficiency": efficiency, "sell_price": sell_price, "target_margin": target_margin,
        "street_width": street_width, "district": district, "city": city
    }
    
    engine = MasterEngine(inputs)
    results = engine.run_analysis()
    kpis = results['kpis']

    # --- التبويبات الشاملة ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 اللوحة الرئيسية", 
        "💰 التدفقات النقدية", 
        "🎲 المخاطر (الحساسية)", 
        "📝 عرض المستثمر",
        "📥 التصدير والتقرير"
    ])

    # Tab 1: Dashboard
    with tab1:
        # المؤشرات العلوية
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("صافي الربح", f"{kpis['profit']:,.0f} ﷼")
        c2.metric("العائد ROI", f"{kpis['roi']:.2f}%", delta_color="normal" if kpis['roi']>=target_margin else "inverse")
        c3.metric("السعر العادل للأرض", f"{kpis['fair_land']:,.0f} ﷼", delta=f"{kpis['fair_land']-land_price:.0f}")
        c4.metric("رأس المال المطلوب", f"{kpis['peak_cash']:,.0f} ﷼", help="أقصى سيولة تحتاجها")
        
        st.markdown("---")
        
        # الخريطة + توزيع التكاليف
        mc1, mc2 = st.columns([1, 1])
        with mc1:
            st.subheader("📍 موقع الأرض")
            map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
            st.map(map_data, zoom=12)
            st.info(f"الموقع: {city}، {district} \n\n عرض الشارع: {street_width} متر")
        
        with mc2:
            st.subheader("توزيع التكاليف")
            cost_df = pd.DataFrame({
                "البند": ["الأرض", "البناء", "مصاريف إدارية", "صافي الربح"],
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
        st.subheader("تحليل السيولة الزمنية (J-Curve)")
        st.line_chart(results['cash_flow'].set_index("الشهر")['السيولة التراكمية'])
        
        st.subheader("جدول التدفقات الشهري")
        st.dataframe(results['cash_flow'].style.format("{:,.0f}"))

    # Tab 3: Sensitivity
    with tab3:
        st.subheader("ماذا لو؟ (تحليل الحساسية)")
        st.write("تأثير تغير سعر البيع (صفوف) وتكلفة البناء (أعمدة) على العائد ROI:")
        sens_df = engine.sensitivity_matrix(kpis['roi'])
        
        # رسم Heatmap باستخدام Matplotlib
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

    # Tab 4: Pitch Generator
    with tab4:
        st.subheader("مولد العرض الاستثماري (نسخ ولصق)")
        pitch = f"""
        **فرصة استثمارية عقارية في {city} - {district}**
        
        يسرنا عرض فرصة لتطوير أرض سكنية بمساحة {area}م2 على شارع {street_width}م.
        المشروع عبارة عن مبنى سكني مكون من {floors} أدوار، بمساحة بيعية {results['net_sellable']:,.0f}م2.
        
        **أبرز المؤشرات المالية:**
        - إجمالي المبيعات المتوقعة: {kpis['revenue']/1000000:.2f} مليون ريال.
        - صافي الربح التقديري: {kpis['profit']/1000000:.2f} مليون ريال.
        - العائد على الاستثمار (ROI): {kpis['roi']:.2f}%.
        - مدة المشروع: {duration} شهر.
        
        سعر الأرض الحالي {land_price} ريال/م يعتبر فرصة مقارنة بالسعر العادل المحسوب ({kpis['fair_land']:,.0f} ريال).
        """
        st.text_area("نص الرسالة للمستثمرين:", pitch, height=300)

    # Tab 5: Export Report
    with tab5:
        st.subheader("تحميل التقرير النهائي")
        
        # تجهيز البيانات للتحميل
        report_data = {
            "المؤشر": ["المدينة", "الحي", "عرض الشارع", "المساحة", "سعر الأرض", "تكلفة البناء", "سعر البيع", "الإيرادات", "التكلفة الكلية", "صافي الربح", "العائد ROI"],
            "القيمة": [city, district, street_width, area, land_price, const_cost, sell_price, kpis['revenue'], kpis['total_cost'], kpis['profit'], kpis['roi']]
        }
        df_rep = pd.DataFrame(report_data)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.dataframe(df_rep)
        with col_d2:
            csv = df_rep.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 تحميل ملف CSV (اكسل)",
                data=csv,
                file_name=f"feasibility_{city}_{district}.csv",
                mime="text/csv",
            )

else:
    st.info("👈 أدخل البيانات (بما في ذلك الحي وعرض الشارع) واضغط 'تشغيل التحليل'.")
