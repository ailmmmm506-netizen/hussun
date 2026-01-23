import re
import streamlit as st
import pandas as pd
import numpy as np
import data_bot

# ---------- Helpers ----------
ARABIC_NUM_CLEAN = re.compile(r"[^\d\.]+")

def to_num(s):
    # يحول "3,500" أو "3500 ريال" إلى رقم
    if pd.isna(s): 
        return np.nan
    s = str(s).replace(",", "").replace("٬", "").replace("ر.س", "").replace("ريال", "")
    s = re.sub(ARABIC_NUM_CLEAN, "", s)
    return pd.to_numeric(s, errors="coerce")

def normalize_text(s):
    return str(s).strip()

RE_BUILDING = r"مبني|فيلا|شقة|بيت|عمارة|دور|استراحة|محل|مكتب|معرض"
RE_LAND = r"أرض|ارض|أراضي|اراضي|قطعة"

@st.cache_resource
def get_bot():
    return data_bot.RealEstateBot()

@st.cache_data
def get_df():
    bot = get_bot()
    df = bot.df.copy()
    # تأكد الأعمدة الأساسية موجودة
    needed = ['الحي', 'نوع_العقار', 'نوع_العقار_الخام', 'المساحة', 'السعر', 'سعر_المتر']
    for c in needed:
        if c not in df.columns:
            df[c] = np.nan

    # توحيد النصوص
    df['الحي'] = df['الحي'].astype(str).str.strip()
    df['نوع_العقار'] = df['نوع_العقار'].astype(str).str.strip()
    df['نوع_العقار_الخام'] = df['نوع_العقار_الخام'].astype(str).str.strip()

    # تحويل رقمي
    df['المساحة'] = df['المساحة'].apply(to_num)
    df['السعر'] = df['السعر'].apply(to_num)
    df['سعر_المتر'] = df['سعر_المتر'].apply(to_num)

    # تنظيف بسيط للقيم غير المنطقية
    df = df[(df['المساحة'] > 10) & (df['المساحة'] < 200000)]
    df = df[(df['سعر_المتر'] > 100) & (df['سعر_المتر'] < 150000)]
    return df

# ---------- Load ----------
df = get_df()

# زر تحديث أنظف
with st.sidebar:
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------- Filtering Example ----------
district_df = df[df['الحي'] == selected_dist].copy()

# أراضي: لازم فيها كلمة أرض، ولازم ما فيها كلمات مباني (في النوعين)
lands_raw = district_df[
    (district_df['نوع_العقار'].str.contains(RE_LAND, regex=True, na=False) |
     district_df['نوع_العقار_الخام'].str.contains(RE_LAND, regex=True, na=False))
    &
    (~district_df['نوع_العقار'].str.contains(RE_BUILDING, regex=True, na=False))
    &
    (~district_df['نوع_العقار_الخام'].str.contains(RE_BUILDING, regex=True, na=False))
]

builds_raw = district_df[
    district_df['نوع_العقار'].str.contains(RE_BUILDING, regex=True, na=False) |
    district_df['نوع_العقار_الخام'].str.contains(RE_BUILDING, regex=True, na=False)
]
