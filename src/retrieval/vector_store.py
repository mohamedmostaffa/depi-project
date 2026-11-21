"""
BrandMind — Persistent ChromaDB Vector Store
Enforces cosine similarity distance and mandatory brand_id isolation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings

from src.retrieval.embeddings import EmbeddingService
from src.schemas import RetrievedChunk


class VectorStore:
    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "brandmind_knowledge",
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_service = embedding_service or EmbeddingService()

        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        # Ensure cosine metric explicitly
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def index_chunks_file(self, chunks_jsonl_path: str = "data/processed/rlvnt/chunks.jsonl") -> int:
        """Loads semantic chunks from JSONL, embeds them, and upserts into ChromaDB."""
        path = Path(chunks_jsonl_path)
        if not path.exists():
            raise FileNotFoundError(f"Chunks file not found: {path}")

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                ids.append(data["chunk_id"])
                documents.append(data["content"])
                metadatas.append({
                    "brand_id": data["brand_id"],
                    "source_file": data["source_file"],
                    "source_page": data["source_page"],
                    "document_type": data["document_type"],
                    "section": data["section"],
                })

        if not documents:
            return 0

        # Generate embeddings
        embeddings = self.embedding_service.embed_texts(documents)

        # Upsert into Chroma collection
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(ids)

    def query(
        self,
        query_text: str,
        brand_id: str,
        top_k: int = 4,
    ) -> List[RetrievedChunk]:
        """Queries collection enforcing strict brand_id metadata isolation."""
        if not brand_id:
            raise ValueError("brand_id is required for all vector retrieval queries")

        query_emb = self.embedding_service.embed_query(query_text)

        # Query collection with brand isolation
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            where={"brand_id": brand_id},
            include=["documents", "metadatas", "distances"],
        )

        retrieved: List[RetrievedChunk] = []

        if not results or not results["ids"] or not results["ids"][0]:
            return retrieved

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, content, meta, dist in zip(ids, docs, metas, distances):
            # Chroma returns cosine distance in [0, 2]; similarity = 1.0 - (dist / 2.0) or 1.0 - dist
            # For unit vectors in hnsw:space cosine, distance = 1 - cosine_sim, so sim = 1.0 - distance
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    brand_id=meta["brand_id"],
                    source_file=meta["source_file"],
                    source_page=int(meta["source_page"]),
                    document_type=meta["document_type"],
                    section=meta["section"],
                    content=content,
                    similarity_score=round(similarity, 4),
                )
            )

        return retrieved
