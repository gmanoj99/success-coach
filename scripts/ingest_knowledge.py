from pathlib import Path
from services.embedding_service import get_embedding
import chromadb

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter
)

from services.embedding_service import (
    get_embedding
)

CHROMA_PATH = "data/chroma"

COLLECTION_NAME = "course_knowledge"


def build_chunks():

    knowledge_path = Path(
        "knowledge.md"
    )

    text = knowledge_path.read_text(
        encoding="utf-8"
    )

    headers = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3")
    ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers
    )

    documents = splitter.split_text(
        text
    )

    chunks = []

    for doc in documents:

        metadata = doc.metadata

        section = " > ".join(
            metadata.values()
        )

        chunks.append(
            {
                "text": doc.page_content,
                "section": section
            }
        )

    return chunks


def ingest():

    chunks = build_chunks()

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    try:
        client.delete_collection(
            COLLECTION_NAME
        )
    except:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME
    )

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for idx, chunk in enumerate(chunks):

        ids.append(
            f"chunk_{idx}"
        )

        documents.append(
            chunk["text"]
        )

        metadatas.append(
            {
                "section": chunk["section"]
            }
        )

        embeddings.append(
            get_embedding(
                chunk["text"]
            )
        )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(
        f"Indexed {len(chunks)} chunks"
    )


if __name__ == "__main__":
    ingest()