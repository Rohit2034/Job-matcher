import os
from dotenv import load_dotenv
from pymongo import MongoClient
import numpy as np

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "jobmatcher")

_mongo_client = MongoClient(MONGO_URI)
_db = _mongo_client[MONGO_DB]

print(" MongoDB connected:", MONGO_URI, "DB:", MONGO_DB)


class CollectionWrapper:
    def __init__(self, db, name: str):
        self._col = db[name]

    def add(self, ids, documents, embeddings, metadatas):
        for _id, doc, emb, meta in zip(ids, documents, embeddings, metadatas):
            self._col.replace_one(
                {"_id": _id},
                {"_id": _id, "document": doc, "embedding": emb, "metadata": meta},
                upsert=True,
            )

    def get(self, ids):
        documents = []
        metadatas = []
        for _id in ids:
            r = self._col.find_one({"_id": _id})
            if r:
                documents.append(r.get("document"))
                metadatas.append(r.get("metadata"))
            else:
                documents.append(None)
                metadatas.append(None)

        return {"documents": documents, "metadatas": metadatas, "ids": ids}

    def query(self, query_texts, n_results: int = 10):
        from embedder import embed

        results_ids = []
        results_distances = []
        results_metadatas = []

        # load all docs once
        all_docs = list(self._col.find({"embedding": {"$exists": True}}))

        for q in query_texts:
            q_emb = np.array(embed(q))

            sims = []
            for d in all_docs:
                emb = np.array(d.get("embedding", []))
                denom = (np.linalg.norm(q_emb) * np.linalg.norm(emb))
                cos = float(np.dot(q_emb, emb) / (denom if denom != 0 else 1e-10))
                # store as distance = 1 - cosine_similarity to match previous semantics
                dist = 1.0 - cos
                sims.append((d["_id"], dist, d.get("metadata"), d.get("document")))

            sims.sort(key=lambda x: x[1])
            top = sims[:n_results]

            ids = [t[0] for t in top]
            distances = [t[1] for t in top]
            metadatas = [t[2] for t in top]

            results_ids.append(ids)
            results_distances.append(distances)
            results_metadatas.append(metadatas)

        return {"ids": results_ids, "distances": results_distances, "metadatas": results_metadatas}


class Client:
    def __init__(self, db):
        self._db = db

    def get_or_create_collection(self, name: str):
        return CollectionWrapper(self._db, name)

    def get_collection(self, name: str):
        return CollectionWrapper(self._db, name)


client = Client(_db)
