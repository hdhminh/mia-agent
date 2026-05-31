import os
from typing import List, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastembed import TextEmbedding


MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/models")

app = FastAPI(title="mia-memory-embedder")
embedding_model = TextEmbedding(model_name=MODEL_NAME, cache_dir=MODEL_CACHE_DIR)


class EmbedRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)
    input_type: Literal["query", "passage"] = "passage"


class EmbedResponse(BaseModel):
    model: str
    dimension: int
    input_type: str
    embeddings: List[List[float]]


def prepare_texts(texts: List[str], input_type: str) -> List[str]:
    cleaned = [str(text or "").strip() for text in texts]
    if "e5" not in MODEL_NAME.lower():
        return cleaned
    prefix = "query: " if input_type == "query" else "passage: "
    prepared = []
    for text in cleaned:
        lowered = text.lower()
        if lowered.startswith("query: ") or lowered.startswith("passage: "):
            prepared.append(text)
        else:
            prepared.append(prefix + text)
    return prepared


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest) -> EmbedResponse:
    texts = prepare_texts(request.texts, request.input_type)
    if not texts:
        return EmbedResponse(model=MODEL_NAME, dimension=384, input_type=request.input_type, embeddings=[])

    embeddings = [list(vector) for vector in embedding_model.embed(texts)]
    dimension = len(embeddings[0]) if embeddings else 384
    return EmbedResponse(
        model=MODEL_NAME,
        dimension=dimension,
        input_type=request.input_type,
        embeddings=embeddings,
    )
