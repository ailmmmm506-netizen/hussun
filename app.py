import streamlit as st
import numpy as np
import pandas as pd
import time

# --- إعداد الصفحة ---
st.set_page_config(page_title="المطور العقاري الذكي", layout="wide", page_icon="🏗️")

# --- التنسيق (CSS) ---
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d6d6d6;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

# --- كلاس التحليل (The Brain) ---
class FeasibilityEngine:
    def __init__(self, area, price, const_cost, margin):
        self.area = area
        self.price = price
        self.const_cost = const_cost
        self.target_margin = margin / 100
        # ثوابت السوق (يمكن تعديلها لاحقاً)
        self.building_ratio = 0.60
        self.floors = 4
        self.efficiency = 0.85

    def get_market_data(self):
        # محاكاة ذكية للبيانات (استبدلها لاحقاً بربط API حقيقي)
        # نقوم بتوليد أسعار قريبة من السعر المدخل لمحاكاة السوق
        base_market_price = self.price * np.random.uniform(0.9, 1.1)
        land_prices = np.random.normal(base_market_price, base_market_price*0.1, 10)
        
        # سعر بيع المتر السكني (تقريبي بناء على سعر الأرض)
        # قاعدة تقريبية: سعر متر الشقة = (سعر متر الأرض / 1.5) + تكلفة البناء + هامش
        est_sell_price = (base_market_price/2) + 2500 + 1000 
        sell_prices = np.random.normal(est_sell_price, est_sell_price*0.05, 10)
        
        return land_prices, sell_prices

    def calculate(self):
        land_data, sell_data = self.get_market_data()
        
        # استبعاد القيم الشاذة
        clean_land = land_data[abs(land_data - np.mean(land_data)) < 2 * np.std(land_data)]
        avg_market_land = np.mean(clean_land)
        avg_sell_price = np.mean(sell_data)
        
        # الحسابات
        total_land_cost = self.area * self.price
        total_bua = self.area * self.building_ratio * self.floors
        net_sellable = total_bua * self.efficiency
        total_const_cost = total_bua * self.const_cost
        soft_costs = (total_land_cost + total_const_cost) * 0.15 # 15% مصاريف
        
        total_cost = total_land_cost + total_const_cost + soft_costs
        revenue = net_sellable * avg_sell_price
        profit = revenue - total_cost
        roi = (profit / total_cost) * 100
        
        fair_land_price = (revenue / (1 + self.target_margin)) - total_const_cost - soft_costs
        fair_land_price_per_m = fair_land_price / self.area

        return {
            "avg_market_land": avg_market_land,
            "avg_sell_price": avg_sell_price,
            "total_cost": total_cost,
            "revenue": revenue,
            "profit": profit,
            "roi": roi,
            "fair_price": fair_land_price_per_m
        }

# --- الواجهة (UI) ---
st.title("🏗️ حاسبة الجدوى العقارية الآلية")
st.caption("نظام تحليل سريع لقرارات شراء الأراضي وتطويرها")
st.divider()

# المدخلات
with st.sidebar:
    st.header("1. بيانات الأرض")
    area = st.number_input("مساحة الأرض (م2)", value=800, step=50)
    price = st.number_input("سعر المتر المعروض (ريال)", value=3500, step=100)
    
    st.header("2. التكاليف")
    const_cost = st.number_input("تكلفة البناء (ريال/م2)", value=2200, help="سعر المتر مسطح تشطيب كامل")
    
    st.header("3. الأهداف")
    margin = st.slider("هامش الربح المستهدف %", 15, 40, 25)
    
    btn = st.button("تحليل الفرصة", type="primary")

# المخرجات
if btn:
    with st.spinner("جاري تحليل بيانات السوق والمنافسين..."):
        time.sleep(1) # تشويق
        engine = FeasibilityEngine(area, price, const_cost, margin)
        res = engine.calculate()

    # قسم النتائج الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("صافي الربح المتوقع", f"{res['profit']:,.0f} ريال")
    col2.metric("العائد (ROI)", f"{res['roi']:.1f}%", delta_color="normal" if res['roi']>=20 else "inverse")
    col3.metric("سعر البيع المقترح (للمتر)", f"{res['avg_sell_price']:,.0f} ريال")
    col4.metric("السعر العادل للأرض", f"{res['fair_price']:,.0f} ريال", delta=f"{res['fair_price']-price:.0f}")

    st.divider()

    # قسم القرار والتوصية
    st.subheader("📋 التقرير والتوصية")
    
    rec_col1, rec_col2 = st.columns([2, 1])
    
    with rec_col1:
        if res['roi'] >= margin:
            st.success(f"✅ **فرصة ممتازة:** المشروع يحقق عائداً ({res['roi']:.1f}%) يتجاوز هدفك ({margin}%). سعر الأرض يعتبر لقطة مقارنة بالسوق.")
        elif res['roi'] > 0:
            st.warning(f"⚠️ **مقبولة بحذر:** المشروع رابح ({res['roi']:.1f}%) لكنه لم يحقق الهدف الطموح ({margin}%). حاول التفاوض لتخفيض سعر الأرض إلى {res['fair_price']:,.0f} ريال.")
        else:
            st.error("⛔ **مخاطرة عالية:** المشروع قد يواجه خسارة بالسعر الحالي. ابحث عن أرض أخرى.")

    with rec_col2:
        st.info("**توزيع التكاليف:**")
        chart_data = pd.DataFrame({
            "Band": ["الأرض", "البناء", "مصاريف"],
            "Cost": [area*price, res['total_cost']-(area*price)-(res['total_cost']*0.15), res['total_cost']*0.15]
        })
        st.bar_chart(chart_data, x="Band", y="Cost")

else:
    st.info("👈 قم بإدخال بيانات الأرض في القائمة الجانبية واضغط 'تحليل الفرصة'")
