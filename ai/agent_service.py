import inspect
import json

from database import load_from_db

from .config import MODEL_NAME, RAG_TOP_K, get_openai_client
from .data_helpers import clean_records, detect_default_columns
from .pandas_tools import TOOL_HANDLERS
from .rag_memory import format_rag_context, retrieve_similar_history, save_chat_turn
from .tool_schemas import TOOLS


def _prefers_pie_chart(user_query):
    query = str(user_query or "").lower()
    pie_keywords = [
        "ulush",
        "foiz",
        "taqsimot",
        "struktur",
        "distribution",
        "share",
        "ratio",
        "proportion",
    ]
    return any(keyword in query for keyword in pie_keywords)


def _extract_chart_from_result(tool_name, result, user_query):
    if not isinstance(result, dict) or result.get("error"):
        return None

    # Explicit chart payload produced by prepare_chart_data tool.
    chart = result.get("chart")
    if isinstance(chart, dict):
        data = chart.get("data")
        chart_type = chart.get("chart_type")
        if isinstance(data, list) and data and chart_type:
            return chart

    if tool_name == "trend_over_time":
        rows = result.get("rows")
        metric = result.get("metric")
        if isinstance(rows, list) and rows and metric:
            return {
                "chart_type": "line",
                "title": f"Trend ({metric})",
                "x": "period",
                "y": metric,
                "data": rows,
            }

    if tool_name == "group_metric":
        rows = result.get("rows")
        group_column = result.get("group_column")
        metric = result.get("metric")
        if isinstance(rows, list) and rows and group_column and metric:
            chart_type = "pie" if _prefers_pie_chart(user_query) and len(rows) <= 12 else "bar"
            return {
                "chart_type": chart_type,
                "title": f"{group_column} bo'yicha {metric}",
                "x": group_column,
                "y": metric,
                "names": group_column,
                "values": metric,
                "data": rows,
            }

    if tool_name == "list_unique_values":
        rows = result.get("rows")
        column = result.get("column")
        if isinstance(rows, list) and rows and column:
            chart_rows = [{column: row.get("value"), "count": row.get("count")} for row in rows]
            chart_type = "pie" if _prefers_pie_chart(user_query) and len(chart_rows) <= 12 else "bar"
            return {
                "chart_type": chart_type,
                "title": f"{column} bo'yicha taqsimot",
                "x": column,
                "y": "count",
                "names": column,
                "values": "count",
                "data": chart_rows,
            }

    return None


def _collect_chart_payloads(tool_results, user_query, max_charts=3):
    charts = []
    seen_keys = set()

    for item in tool_results:
        tool_name = item.get("tool")
        result = item.get("result")
        chart = _extract_chart_from_result(tool_name, result, user_query)
        if chart is None:
            continue

        dedupe_payload = {
            "chart_type": chart.get("chart_type"),
            "x": chart.get("x"),
            "y": chart.get("y"),
            "names": chart.get("names"),
            "values": chart.get("values"),
            "data": chart.get("data"),
        }
        chart_key = json.dumps(dedupe_payload, sort_keys=True, ensure_ascii=False)
        if chart_key in seen_keys:
            continue

        seen_keys.add(chart_key)
        charts.append(chart)
        if len(charts) >= max_charts:
            break

    return charts


def _format_agent_output(answer, charts, return_payload):
    if return_payload:
        return {
            "answer": answer,
            "charts": charts or [],
        }
    return answer


def _build_data_context(df):
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "detected": detect_default_columns(df),
        "sample": clean_records(df.head(3)),
    }


def _parse_tool_args(arguments):
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        return {}


def _execute_tool(tool_name, args, df):
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return {"ok": False, "tool": tool_name, "error": f"Noma'lum tool: {tool_name}"}

    try:
        signature = inspect.signature(handler)
        accepted_params = set(signature.parameters.keys())
        filtered_args = {key: value for key, value in args.items() if key in accepted_params and key != "df"}
        result = handler(df, **filtered_args)
        if isinstance(result, dict) and result.get("error"):
            return {"ok": False, "tool": tool_name, "error": result.get("error"), "result": result}
        return {"ok": True, "tool": tool_name, "result": result}
    except Exception as exc:
        return {"ok": False, "tool": tool_name, "error": str(exc)}


def get_agent_response(user_query, session_id="default", return_payload=False):
    user_query = str(user_query).strip()
    if not user_query:
        return _format_agent_output("Iltimos, savol kiriting.", charts=[], return_payload=return_payload)

    df = load_from_db()
    if df is None or df.empty:
        return _format_agent_output(
            "Ma'lumotlar topilmadi. Iltimos, fayl yuklang.",
            charts=[],
            return_payload=return_payload,
        )

    client = get_openai_client()
    if client is None:
        return _format_agent_output(
            "OPENAI_API_KEY topilmadi. Iltimos, .env faylini tekshiring.",
            charts=[],
            return_payload=return_payload,
        )

    data_context = _build_data_context(df)
    rag_rows = retrieve_similar_history(session_id=session_id, query=user_query, top_k=RAG_TOP_K)
    rag_context = format_rag_context(rag_rows)

    system_prompt = (
        "Siz Uzbek tilida ishlaydigan tajribali savdo analitik yordamchisiz. "
        "Agar hisob-kitob kerak bo'lsa, albatta tool chaqiring va aniq raqamlarga tayaning. "
        "Savolda taqsimot/ulush/trend/taqqoslash so'ralgan bo'lsa prepare_chart_data toolini ham chaqiring "
        "va chart turini mos tanlang (ulush=pie, trend=line, taqqoslash=bar, bog'liqlik=scatter). "
        "RAG orqali berilgan oldingi suhbatlardan foydali joylarini ishlating, "
        "lekin doim joriy dataset tool natijasini ustun qo'ying."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Dataset context: {json.dumps(data_context, ensure_ascii=False)}",
        },
        {
            "role": "system",
            "content": f"RAG context (o'xshash oldingi suhbatlar):\n{rag_context}",
        },
        {"role": "user", "content": user_query},
    ]

    final_answer = None
    executed_tools = []

    try:
        for _ in range(6):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg.model_dump(exclude_none=True))
                for tool_call in msg.tool_calls:
                    tool_args = _parse_tool_args(tool_call.function.arguments)
                    tool_result = _execute_tool(tool_call.function.name, tool_args, df)
                    executed_tools.append(tool_result)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )
                continue

            if msg.content:
                final_answer = msg.content.strip()
                break

        if not final_answer:
            final_answer = "Javobni shakllantirish uchun urinishlar chegarasiga yetildi. Savolni aniqroq yozib qayta yuboring."

        save_chat_turn(
            session_id=session_id,
            user_query=user_query,
            assistant_response=final_answer,
        )

        charts = _collect_chart_payloads(executed_tools, user_query=user_query)
        return _format_agent_output(final_answer, charts=charts, return_payload=return_payload)

    except Exception as exc:
        return _format_agent_output(
            f"Xatolik yuz berdi: {str(exc)}",
            charts=[],
            return_payload=return_payload,
        )
