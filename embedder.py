import re
import numpy as np
import os

_model = None
_embedding_fn = None
_model_dim = 384

_chroma_onnx_path = os.path.join(os.path.expanduser("~"), ".cache", "chroma", "onnx_models", "all-MiniLM-L6-v2", "onnx")
if os.path.isdir(_chroma_onnx_path):
    try:
        from chromadb.utils import embedding_functions

        try:
            _embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
            print("Using local ONNX MiniLM model from:", _chroma_onnx_path)
        except Exception:
            _embedding_fn = None
    except Exception:
        _embedding_fn = None

if _embedding_fn is None:
    try:
        from sentence_transformers import SentenceTransformer

        try:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            print("Using SentenceTransformer all-MiniLM-L6-v2")
        except Exception:
            _model = None
            print("SentenceTransformer model unavailable; will use fallback embeddings")
    except Exception:
        _model = None
        print("sentence-transformers package not available; will use fallback embeddings")


def _fallback_embed(text: str, dim: int = 384) -> list[float]:
    vec = np.zeros(dim, dtype=float)
    tokens = re.findall(r"\w+", (text or "").lower())
    if not tokens:
        return [0.0] * dim

    for t in tokens:
        idx = (hash(t) & 0xFFFFFFFF) % dim
        vec[idx] += 1.0

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()


def embed(text: str) -> list[float]:
    if not text or len(text.strip()) == 0:
        return [0.0] * _model_dim

    if _embedding_fn is not None:
        try:
            emb = _embedding_fn([text])[0]
            # Convert numpy array to list if needed (for MongoDB BSON compatibility)
            if hasattr(emb, 'tolist'):
                return emb.tolist()
            return list(emb) if not isinstance(emb, list) else emb
        except Exception:
            print("Local ONNX embedding failed; falling back")

    if _model is not None:
        try:
            emb = _model.encode([text], convert_to_numpy=True)[0]
            return emb.tolist()
        except Exception:
            print("Failed to encode with SentenceTransformer; using fallback embedding")

    return _fallback_embed(text, dim=_model_dim)