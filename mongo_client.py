import os
from dotenv import load_dotenv
from pymongo import MongoClient
import numpy as np

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "jobmatcher")

_mongo_client = MongoClient(MONGO_URI)
_db = _mongo_client[MONGO_DB]

print("MongoDB connected:", MONGO_URI, "DB:", MONGO_DB)


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


class Client:
    def __init__(self, db):
        self._db = db

    def get_collection(self, name: str):
        return CollectionWrapper(self._db, name)


client = Client(_db)
