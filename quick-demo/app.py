# --- MUST BE FIRST: sanitize env before any imports ---
import os, re

# 可選：關掉 HF tokenizers 的平行化警告
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# 若使用 .env，先載入
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

raw = os.getenv("GROQ_API_KEY", "")

# 1) 去除所有空白類字元（空格、\t、\n、\r 等）
clean = re.sub(r"\s+", "", raw)

# 2) 去除前後引號（有些人會寫成 GROQ_API_KEY="gsk_xxx" 並連帶進來）
clean = clean.strip("\"'")

# 3) 基本格式檢查（Groq 金鑰通常以 gsk_ 開頭，僅字母數字與破折號底線）
if not (clean.startswith("gsk_") and re.fullmatch(r"[A-Za-z0-9_\-]+", clean)):
    raise RuntimeError(
        "Invalid GROQ_API_KEY format after sanitization. "
        "Please re-copy your key from Groq Console (no spaces/quotes/newlines)."
    )

# 4) 覆寫回環境，之後 Groq SDK/你自己的程式讀到的都是乾淨的
os.environ["GROQ_API_KEY"] = clean

# 5) 安全檢查（不印出金鑰）：檢查長度 & 最後一字元的 ASCII
#    若最後字元不是可列印字元（例如 \r=13 或 \n=10），就會抓到
last_ord = ord(clean[-1])
if last_ord < 32 or last_ord == 127:
    raise RuntimeError(f"GROQ_API_KEY contains non-printable char at end: ord={last_ord}")

# 6) 初始化 Groq client（用乾淨的 key）
from groq import Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])


import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from groq import Groq
import streamlit as st

# -------- 初始化 --------
# 1. 載入模型
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

uploaded_file = st.file_uploader("Upload a PDF", type="pdf")
if uploaded_file:
    pdf = PdfReader(uploaded_file)
    raw = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_text(raw)

    # 建立向量索引
    emb = embedder.encode(chunks, normalize_embeddings=True)
    emb = np.array(emb, dtype="float32")
    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    st.success("PDF processed! You can now ask questions.")
else:
    st.warning("Please upload a PDF to start.")
    st.stop()


# -------- Memory 類別 --------
class Memory:
    def __init__(self, max_turns=5):
        self.turns = []
        self.max_turns = max_turns
    def add(self, q, a):
        self.turns.append((q,a))
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)
    def text(self):
        return "\n".join([f"User: {q}\nAI: {a}" for q,a in self.turns])

memory = Memory()

# -------- 檢索 --------
def search(query, k=5):
    qv = embedder.encode([query], normalize_embeddings=True).astype("float32")
    D, I = index.search(qv, k)
    return [chunks[i] for i in I[0]]

# -------- RAG 對話 --------
def chat(question, k=5):
    history = memory.text()
    ctx = "\n".join(search(question, k))
    messages = [
        {"role": "system", "content": "You are a precise assistant. Use CONTEXT and HISTORY."},
        {"role": "user", "content": f"HISTORY:\n{history}\n\nCONTEXT:\n{ctx}\n\nQUESTION: {question}"}
    ]
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.0,
        max_tokens=400
    )
    answer = resp.choices[0].message.content
    memory.add(question, answer)
    return answer

# -------- Streamlit UI --------
st.title("PDF RAG Chatbot")

question = st.text_input("Ask a question:")
if st.button("Submit") and question:
    answer = chat(question)
    st.write("**Answer:**", answer)
