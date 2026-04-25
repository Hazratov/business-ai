import inspect
import json

from database import load_from_db

from .config import MODEL_NAME, RAG_TOP_K, get_openai_client
from .data_helpers import clean_records, detect_default_columns
from .pandas_tools import TOOL_HANDLERS
from .rag_memory import format_rag_context, retrieve_similar_history, save_chat_turn
from .tool_schemas import TOOLS


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
        return {"error": f"Noma'lum tool: {tool_name}"}

    try:
        signature = inspect.signature(handler)
        accepted_params = set(signature.parameters.keys())
        filtered_args = {key: value for key, value in args.items() if key in accepted_params and key != "df"}
        result = handler(df, **filtered_args)
        return {"ok": True, "tool": tool_name, "result": result}
    except Exception as exc:
        return {"ok": False, "tool": tool_name, "error": str(exc)}


def get_agent_response(user_query, session_id="default"):
    user_query = str(user_query).strip()
    if not user_query:
        return "Iltimos, savol kiriting."

    df = load_from_db()
    if df is None or df.empty:
        return "Ma'lumotlar topilmadi. Iltimos, fayl yuklang."

    client = get_openai_client()
    if client is None:
        return "OPENAI_API_KEY topilmadi. Iltimos, .env faylini tekshiring."

    data_context = _build_data_context(df)
    rag_rows = retrieve_similar_history(session_id=session_id, query=user_query, top_k=RAG_TOP_K)
    rag_context = format_rag_context(rag_rows)

    system_prompt = (
        "Siz Uzbek tilida ishlaydigan tajribali savdo analitik yordamchisiz. "
        "Agar hisob-kitob kerak bo'lsa, albatta tool chaqiring va aniq raqamlarga tayaning. "
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

        return final_answer

    except Exception as exc:
        return f"Xatolik yuz berdi: {str(exc)}"
