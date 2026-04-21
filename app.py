import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, save_to_db, load_from_db
import os

# Page configuration
st.set_page_config(page_title="Sotuv Ma'lumotlari Analizatori", layout="wide")

# Initialize database
init_db()

# Uzbek UI Translations
T = {
    "title": "📊 Sotuv Ma'lumotlari Analizatori",
    "upload_section": "📁 Ma'lumotlarni yuklash",
    "upload_help": "CSV yoki Excel faylini tanlang",
    "data_view": "📋 Ma'lumotlar jadvali",
    "metrics": "📈 Asosiy ko'rsatkichlar",
    "total_sales": "Umumiy savdo",
    "total_orders": "Buyurtmalar soni",
    "avg_order": "O'rtacha chek",
    "charts": "📊 Grafiklar",
    "top_products": "Top Mahsulotlar",
    "sales_by_region": "Hududlar bo'yicha sotuv",
    "agent_section": "🤖 Sun'iy Intellekt Analitigi",
    "ask_placeholder": "Savolingizni yozing (masalan: Eng ko'p sotilgan mahsulot qaysi?)",
    "send_btn": "So'rash",
    "no_data": "Iltimos, tahlil qilish uchun ma'lumot yuklang.",
    "success_upload": "Fayl muvaffaqiyatli yuklandi!"
}

def find_column(df, keywords):
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in keywords):
            return col
    return None

def main():
    st.title(T["title"])

    # Sidebar for file upload
    with st.sidebar:
        st.header(T["upload_section"])
        uploaded_file = st.file_uploader(T["upload_help"], type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                save_to_db(df)
                st.success(T["success_upload"])
            except Exception as e:
                st.error(f"Xatolik: {e}")

    # Load data from DB
    df = load_from_db()

    if df is not None:
        # Data Mapping
        sales_col = find_column(df, ['jami', 'total', 'amount', 'price', 'summa', 'sotuv'])
        prod_col = find_column(df, ['mahsulot', 'product', 'item', 'nomi'])
        region_col = find_column(df, ['hudud', 'region', 'city', 'shahar', 'manzil'])
        
        # Metrics Row
        st.subheader(T["metrics"])
        col1, col2, col3 = st.columns(3)
        
        total_sales = df[sales_col].sum() if sales_col else 0
        total_orders = len(df)
        avg_order = total_sales / total_orders if total_orders > 0 else 0

        col1.metric(T["total_sales"], f"{total_sales:,.0f}")
        col2.metric(T["total_orders"], f"{total_orders:,}")
        col3.metric(T["avg_order"], f"{avg_order:,.2f}")

        # Dataframe View
        with st.expander(T["data_view"]):
            st.dataframe(df, use_container_width=True)

        # Charts Row
        st.subheader(T["charts"])
        c1, c2 = st.columns(2)

        # Top Products Chart
        if prod_col and sales_col:
            top_df = df.groupby(prod_col)[sales_col].sum().sort_values(ascending=False).head(10).reset_index()
            fig1 = px.bar(top_df, x=prod_col, y=sales_col, title=T["top_products"], color=sales_col)
            c1.plotly_chart(fig1, use_container_width=True)
        
        # Regional Analysis Chart
        if region_col and sales_col:
            reg_df = df.groupby(region_col)[sales_col].sum().reset_index()
            fig2 = px.pie(reg_df, values=sales_col, names=region_col, title=T["sales_by_region"])
            c2.plotly_chart(fig2, use_container_width=True)

        # AI Agent Section
        st.divider()
        st.subheader(T["agent_section"])
        user_input = st.text_input(T["ask_placeholder"])
        if st.button(T["send_btn"]):
            if user_input:
                with st.spinner("Agent tahlil qilmoqda..."):
                    from agent import get_agent_response
                    response = get_agent_response(user_input)
                    st.markdown(f"**Javob:**\n\n{response}")
            else:
                st.warning("Iltimos, savol kiriting.")
    else:
        st.info(T["no_data"])

if __name__ == "__main__":
    main()
