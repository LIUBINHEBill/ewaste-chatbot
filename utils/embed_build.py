# utils/embed_build.py
import os, re, pickle, numpy as np, faiss
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv()

### 1) 初始化 OpenAI 客户端 ###
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMB_MODEL = "text-embedding-3-small"

DATA_DIR   = Path("knowledge_base")
CHUNK_SIZE = 450

def clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()

def split_chunks(text: str, size=CHUNK_SIZE):
    return [text[i:i+size] for i in range(0, len(text), size)]

docs, meta = [], []
for file in DATA_DIR.glob("*.txt"):
    raw = clean(file.read_text(encoding="utf-8"))
    for i, chunk in enumerate(split_chunks(raw)):
        docs.append(chunk)
        meta.append({"file": file.name, "chunk": i})

print("Total chunks:", len(docs))

### 2) 生成嵌入 ###
embeddings = []
for chunk in docs:
    resp = client.embeddings.create(model=EMB_MODEL, input=[chunk])
    embeddings.append(resp.data[0].embedding)

embeddings = np.array(embeddings, dtype="float32")
faiss.normalize_L2(embeddings)

### 3) 建立 & 保存索引 ###
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, "kb.index")
pickle.dump({"docs": docs, "meta": meta}, open("kb.pkl", "wb"))

print("✅  Saved kb.index  &  kb.pkl")
