from openai import OpenAI
import pandas as pd
from database import load_from_db
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_agent_response(user_query):
    df = load_from_db()
    if df is None:
        return "Ma'lumotlar topilmadi. Iltimos, fayl yuklang."

    # Prepare data context for the LLM
    # We send a summary of the data to keep the context window small
    data_summary = {
        "columns": list(df.columns),
        "shape": df.shape,
        "sample": df.head(5).to_dict(),
        "description": df.describe(include='all').to_dict()
    }

    prompt = f"""
    Siz ma'lumotlar tahlilchisi agentsiz. Quyidagi ma'lumotlar to'plami (sales data) bo'yicha foydalanuvchi savoliga javob bering.
    
    Ma'lumotlar haqida qisqacha:
    - Ustunlar: {data_summary['columns']}
    - Jami qatorlar: {data_summary['shape'][0]}
    - Namuna: {data_summary['sample']}
    
    Foydalanuvchi savoli: "{user_query}"
    
    Ko'rsatmalar:
    1. Javobni o'zbek tilida bering.
    2. Ma'lumotlarga asoslanib aniq faktlar va raqamlarni keltiring.
    3. Agar savolga javob berish uchun hisob-kitob kerak bo'lsa, mantiqiy tushuntiring.
    4. Professional va yordam beruvchi ohangda bo'ling.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz tajribali ma'lumotlar tahlilchisisiz."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Xatolik yuz berdi: {str(e)}"
