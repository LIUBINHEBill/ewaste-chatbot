# utils/retriever.py
import os, pickle, numpy as np, faiss
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMB_MODEL = "text-embedding-3-small"

index = faiss.read_index("kb.index")
store = pickle.load(open("kb.pkl", "rb"))
docs  = store["docs"]

def search(query: str, k: int = 3) -> list[str]:
    q_vec = client.embeddings.create(model=EMB_MODEL, input=[query]).data[0].embedding
    q_vec = np.array(q_vec, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(q_vec)
    scores, idx = index.search(q_vec, k)
    return [docs[i] for i in idx[0]]
