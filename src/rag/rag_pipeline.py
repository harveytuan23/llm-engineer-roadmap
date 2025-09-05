from groq import Groq
import numpy as np
from .retriever import search_with_meta
from .memory import ConversationMemory, summarize_history_with_groq

# ---- Day3 RAG Answer（帶 history / sources）----
def rag_answer(
    question,
    k=5,
    history_text="",
    sys_prompt=("You are a precise assistant. Answer ONLY using the provided CONTEXT and, if present, "
                "the DIALOG HISTORY SUMMARY. If the answer is not supported by the CONTEXT, reply exactly: "
                "'I don't know based on the provided context.' Be concise."),
    temperature=0.0,
    max_tokens=500,
    return_sources=True
):
    # 檢索
    hits = search_with_meta(question, k=k)
    context_blocks = []
    for h in hits:
        # 給每段一個來源編號，方便引用
        context_blocks.append(f"[{h['idx']}] {h['chunk']}")
    context = "\n\n".join(context_blocks)

    # 可選：長對話時做摘要，避免把整段歷史直接塞進去
    history_summary = history_text.strip()

    user_prompt = (
        (f"DIALOG HISTORY SUMMARY:\n{history_summary}\n\n" if history_summary else "") +
        f"CONTEXT (numbered excerpts):\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Instructions:\n"
        "- Cite the excerpt numbers you used, e.g., (see [12], [34]).\n"
        "- If the answer is not in CONTEXT, say: \"I don't know based on the provided context.\""
    )

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    answer = resp.choices[0].message.content.strip()

    if return_sources:
        sources = [{"idx": h["idx"], "score": h["score"], "snippet": h["chunk"][:300]} for h in hits]
        return {"answer": answer, "sources": sources}
    return answer


# ---- 對話式 RAG ----
memory = ConversationMemory(max_turns=5)

def rag_chat(question, k=5, summarize_if_over_chars=1500):
    # 取得歷史對話
    history_text = memory.get_history_text()

    # 如果歷史太長，先用 Groq 摘要
    if len(history_text) > summarize_if_over_chars:
        history_text = summarize_history_with_groq(history_text, client)

    # 產生答案（含來源）
    result = rag_answer(
        question=question,
        k=k,
        history_text=history_text,
        return_sources=True
    )
    # 存入記憶
    memory.add_turn(question, result["answer"])
    return result
