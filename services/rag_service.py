import chromadb

from services.embedding_service import (
    get_embedding
)

CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "course_knowledge"

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME
)


def retrieve_context(
    query: str,
    top_k: int = 10
):
    query_embedding = get_embedding(
        query
    )

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=top_k
    )

    chunks = []

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(
        docs,
        metas,
        distances
    ):
        chunks.append(
            {
                "text": doc,
                "metadata": meta,
                "distance": dist
            }
        )

    return chunks


def format_kb_context(
    chunks
):
    if not chunks:
        return ""

    formatted = []

    for chunk in chunks:

        section = chunk["metadata"].get(
            "section",
            "Unknown Section"
        )

        formatted.append(
            f"""Section:{section}
            Content:{chunk['text']} """
        )

    return "\n\n".join(
        formatted
    )