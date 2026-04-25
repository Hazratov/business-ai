# Sales AI Agent Texnologiya Hujjati

Sana: 2026-04-25

## 1) Loyihaning maqsadi
Bu agentning vazifasi:
- Foydalanuvchi savolini (Uzbek tilida) qabul qilish.
- Savolga mos pandas hisob-kitoblarini function calling orqali avtomatik tanlash.
- Oldingi o'xshash suhbatlardan RAG orqali kontekst olib, javob sifatini oshirish.
- Yakuniy javobni Uzbek tilida berish.

## 2) Dekompozitsiya (modul arxitektura)
Agent monolit bo'lmasligi uchun logika qatlamlarga bo'lingan:

- app.py: Streamlit UI, fayl yuklash, session boshqaruvi, chatni yuborish.
- agent.py: yupqa wrapper (import/re-export), backward compatibility uchun.
- ai/config.py: model, embedding, RAG sozlamalari va OpenAI client.
- ai/data_helpers.py: ustunlarni aniqlash va umumiy helper funksiyalar.
- ai/pandas_tools.py: barcha analytics tool funksiyalari (sum, group, filter, trend).
- ai/tool_schemas.py: OpenAI function calling JSON schema ta'riflari.
- ai/rag_memory.py: vector DB ga yozish va retrieval (RAG memory qatlami).
- ai/agent_service.py: agent orchestration (RAG + function calling + final answer).

## 3) Ishlatilgan texnologiyalar

### 3.1 UI va analitika
- Streamlit: interaktiv web interfeys.
- Pandas: data manipulation va hisob-kitoblar.
- Plotly: grafiklar (bar, pie).

### 3.2 LLM va function calling
- OpenAI Chat Completions API.
- Model: odatda gpt-4o (OPENAI_MODEL orqali boshqariladi).
- Function calling: tool schema + tool execution loop.

### 3.3 RAG va vector memory
- OpenAI Embeddings API.
- Embedding model: text-embedding-3-small (OPENAI_EMBEDDING_MODEL).
- ChromaDB PersistentClient: local vector DB.
- Storage path: .vectordb/ (gitga kirmaydi).

### 3.4 Data storage
- SQLite (sales_data.db): yuklangan savdo dataseti shu yerda saqlanadi.

## 4) Memory strategiyasi

### 4.1 Short memory (session memory)
- Streamlit session_state ichida saqlanadi:
  - chat_session_id
  - chat_history
- Maqsad: joriy chat sessiyasini izolyatsiya qilish.

### 4.2 Vector memory (longer memory)
- Har bir turn (Savol + Javob) embedding qilinadi.
- Chroma collection ga yoziladi (metadata: session_id, created_at).
- Yangi savolda o'xshash tarix query qilinadi.

### 4.3 Retrieval strategiyasi
- Birinchi urinish: faqat joriy session_id bo'yicha qidirish.
- Agar natija bo'lmasa: global collectiondan fallback qidirish.
- Top natijalar promptga RAG context sifatida qo'shiladi.

## 5) RAG pipeline qanday ishlaydi
1. User savoli keladi.
2. query embedding olinadi.
3. Vector DB dan top_k o'xshash oldingi suhbatlar olinadi.
4. Topilgan hujjatlar formatlanib system contextga qo'shiladi.
5. LLMga quyidagilar beriladi:
   - dataset context
   - RAG context
   - user savoli
6. LLM kerak bo'lsa tool chaqiradi.
7. Tool natijalari qayta LLMga beriladi.
8. Final javob yaratiladi.
9. Shu turn vector DB ga qayta saqlanadi.

## 6) Function calling arxitekturasi
- Tool schema: ai/tool_schemas.py.
- Tool implementatsiya: ai/pandas_tools.py.
- Tool dispatcher: ai/agent_service.py ichidagi _execute_tool.
- Multi-step loop: model bir necha marta tool chaqirishi mumkin.

Ishlatilayotgan asosiy tool lar:
- get_columns
- get_dataset_summary
- aggregate_metric
- group_metric
- filter_metric
- trend_over_time
- list_unique_values

## 7) Prompt va reasoning dizayni
- System prompt Uzbek tilda javob berishni majbur qiladi.
- RAG context alohida system message sifatida beriladi.
- Data aniqligi uchun "hisob-kitob kerak bo'lsa tool chaqir" qoidasi qo'llanadi.
- Temperaturasi past (0.1) qo'yilgan, bu stabil javoblar uchun.

## 8) Sozlamalar (ENV)
Loyiha quyidagi environment variable larni ishlatadi:
- OPENAI_API_KEY: OpenAI API kaliti.
- OPENAI_MODEL: chat model nomi (default gpt-4o).
- OPENAI_EMBEDDING_MODEL: embedding model (default text-embedding-3-small).
- RAG_TOP_K: nechta o'xshash tarix olinishi.
- VECTOR_DB_PATH: vector DB papkasi (default .vectordb).
- VECTOR_COLLECTION: collection nomi.

## 9) Kuzatilgan afzalliklar
- Monolit kod o'rniga modul arxitektura: kengaytirish oson.
- Function calling sababli hisob-kitoblar deterministik va tekshiriladigan.
- RAG sababli kontekst saqlanadi va follow-up savollar sifati oshadi.
- Session-first retrieval sababli chatlar bir-biriga aralashmaydi.

## 10) Hozirgi cheklovlar
- Local vector DB bir server instancega bog'langan.
- Chat memory hozircha turn-level, structured knowledge graph emas.
- Access control va multi-user isolation chuqurlashtirilmagan (session_id asosiy mexanizm).

## 11) Keyingi yaxshilashlar
- Hybrid retrieval (vector + keyword/BM25).
- Reranker qo'shish (top-N ni qayta saralash).
- RAG debug panel (top hujjatlar va similarity score larni UI da ko'rsatish).
- Tool tracing/logging va audit trail.
- Multi-tenant user identity qatlamini qo'shish.
