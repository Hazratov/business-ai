import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
from database import init_db, save_to_db, load_from_db

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
    "send_btn": "Yuborish",
    "new_chat_btn": "Yangi chat",
    "chat_history": "🧠 Chat tarixi",
    "session_label": "Joriy sessiya",
    "no_data": "Iltimos, tahlil qilish uchun ma'lumot yuklang.",
    "success_upload": "Fayl muvaffaqiyatli yuklandi!"
}

def find_column(df, keywords):
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in keywords):
            return col
    return None


def parse_agent_response(response):
    if isinstance(response, dict):
        answer = str(response.get("answer", "")).strip()
        charts = response.get("charts") if isinstance(response.get("charts"), list) else []
        return answer, charts
    return str(response), []


def render_agent_charts(charts):
    if not charts:
        return

    valid_charts = [chart for chart in charts if isinstance(chart, dict)]
    if not valid_charts:
        return

    st.markdown("**Savolga mos grafiklar:**")
    columns = st.columns(2)

    for idx, chart in enumerate(valid_charts[:4]):
        chart_type = str(chart.get("chart_type", "bar")).lower()
        data = chart.get("data")
        if not isinstance(data, list) or not data:
            continue

        frame = pd.DataFrame(data)
        if frame.empty:
            continue

        title = chart.get("title") or "Analitik chart"
        target = columns[idx % 2] if len(valid_charts) > 1 else st

        try:
            if chart_type == "pie":
                names = chart.get("names") or chart.get("x")
                values = chart.get("values") or chart.get("y")
                if names not in frame.columns or values not in frame.columns:
                    continue
                fig = px.pie(frame, names=names, values=values, title=title)
            elif chart_type == "line":
                x = chart.get("x")
                y = chart.get("y")
                if x not in frame.columns or y not in frame.columns:
                    continue
                fig = px.line(frame, x=x, y=y, title=title, markers=True)
            elif chart_type == "scatter":
                x = chart.get("x")
                y = chart.get("y")
                if x not in frame.columns or y not in frame.columns:
                    continue
                fig = px.scatter(frame, x=x, y=y, title=title)
            else:
                x = chart.get("x")
                y = chart.get("y")
                if x not in frame.columns or y not in frame.columns:
                    continue
                fig = px.bar(frame, x=x, y=y, title=title, color=y)

            target.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            target.caption(f"Chart chizishda xatolik: {exc}")

def main():
    st.title(T["title"])

    if "chat_session_id" not in st.session_state:
        st.session_state["chat_session_id"] = str(uuid.uuid4())
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

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

        session_col1, session_col2 = st.columns([3, 1])
        session_col1.caption(f"{T['session_label']}: {st.session_state['chat_session_id']}")
        if session_col2.button(T["new_chat_btn"]):
            st.session_state["chat_session_id"] = str(uuid.uuid4())
            st.session_state["chat_history"] = []
            st.rerun()

        user_input = st.text_input(T["ask_placeholder"])
        if st.button(T["send_btn"]):
            if user_input:
                with st.spinner("Agent tahlil qilmoqda..."):
                    from agent import get_agent_response
                    response = get_agent_response(
                        user_input,
                        session_id=st.session_state["chat_session_id"],
                        return_payload=True,
                    )
                    answer_text, chart_specs = parse_agent_response(response)
                    st.session_state["chat_history"].append(
                        {
                            "question": user_input,
                            "answer": answer_text,
                            "charts": chart_specs,
                        }
                    )
                    st.markdown(f"**Javob:**\n\n{answer_text}")
                    render_agent_charts(chart_specs)
            else:
                st.warning("Iltimos, savol kiriting.")

        if st.session_state["chat_history"]:
            with st.expander(T["chat_history"], expanded=False):
                for item in reversed(st.session_state["chat_history"][-10:]):
                    st.markdown(f"**Savol:** {item['question']}")
                    st.markdown(f"**Javob:** {item['answer']}")
                    render_agent_charts(item.get("charts") or [])
                    st.divider()
    else:
        st.info(T["no_data"])

if __name__ == "__main__":
    main()
