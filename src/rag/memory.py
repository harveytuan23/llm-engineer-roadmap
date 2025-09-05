from groq import Groq

# ---- Conversation Memory (簡單版) ----
class ConversationMemory:
    def __init__(self, max_turns=5):
        self.turns = []
        self.max_turns = max_turns

    def add_turn(self, question, answer):
        self.turns.append({"q": question, "a": answer})
        # 只保留最近 N 回合
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_history_text(self):
        # 轉成可讀的多輪對話字串
        return "\n".join([f"User: {t['q']}\nAssistant: {t['a']}" for t in self.turns])

# ---- Memory Summarizer（可選）----
def summarize_history_with_groq(history_text, client, budget_tokens=400):
    if not history_text.strip():
        return ""
    sys = ("You are a concise assistant. Summarize the dialog into key facts and open intents. "
           "Keep entities, dates, constraints. Max 10 bullet points.")
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": f"Dialog:\n{history_text}\n\nSummarize:"}
        ],
        temperature=0.0,
        max_tokens=budget_tokens
    )
    return resp.choices[0].message.content.strip()
