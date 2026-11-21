"""
Script to index all semantic chunks into persistent ChromaDB storage.
"""

from src.retrieval.vector_store import VectorStore


def main():
    store = VectorStore(persist_dir="./chroma_db")
    count = store.index_chunks_file("data/processed/rlvnt/chunks.jsonl")
    print(f"Successfully indexed {count} chunks into ChromaDB at ./chroma_db")


if __name__ == "__main__":
    main()
