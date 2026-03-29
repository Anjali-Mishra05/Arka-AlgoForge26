"""
vectorbase.py — Pinecone + Cohere RAG utilities.
Uses native SDKs to avoid Python 3.13 / langchain-pinecone dependency conflicts.
"""
import os
from dotenv import load_dotenv
from pinecone import Pinecone
import cohere
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "pravaha-index")
DIRECTORY = "input_documents"

# Lazy-init clients
_pc: Pinecone | None = None
_co: cohere.Client | None = None


def _get_pinecone() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    return _pc


def _get_cohere() -> cohere.Client:
    global _co
    if _co is None:
        _co = cohere.Client(api_key=COHERE_API_KEY)
    return _co


def _embed_texts(texts: list) -> list:
    """Embed a list of strings with Cohere (document input type)."""
    co = _get_cohere()
    response = co.embed(
        texts=texts,
        model="embed-english-v3.0",
        input_type="search_document",
    )
    return response.embeddings


def _embed_query(text: str) -> list:
    """Embed a single query string."""
    co = _get_cohere()
    response = co.embed(
        texts=[text],
        model="embed-english-v3.0",
        input_type="search_query",
    )
    return response.embeddings[0]


class PDFProcessor:
    def __init__(self, index_name: str = INDEX_NAME):
        self.index_name = index_name

    def load_docs(self, directory: str):
        docs = []
        try:
            docs.extend(PyPDFDirectoryLoader(directory).load())
        except Exception as e:
            print(f"PDF loading failed: {e}")
        try:
            docs.extend(DirectoryLoader(directory, glob="**/*.md", loader_cls=TextLoader).load())
        except Exception as e:
            print(f"MD loading failed: {e}")
        return docs

    def split_docs(self, documents):
        return RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=150
        ).split_documents(documents)

    def create_index(self, docs):
        if not docs:
            print("No documents to index.")
            return
        pc = _get_pinecone()
        index = pc.Index(self.index_name)
        batch_size = 96
        upserted = 0
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            texts = [d.page_content for d in batch]
            embeddings = _embed_texts(texts)
            vectors = [
                {
                    "id": f"doc-{i + j}",
                    "values": embeddings[j],
                    "metadata": {"text": texts[j], **batch[j].metadata},
                }
                for j in range(len(batch))
            ]
            index.upsert(vectors=vectors)
            upserted += len(vectors)
        print(f"Upserted {upserted} chunks into '{self.index_name}'")

    def retrieve(self, question: str, top_k: int = 5) -> list:
        pc = _get_pinecone()
        index = pc.Index(self.index_name)
        query_vec = _embed_query(question)
        results = index.query(vector=query_vec, top_k=top_k, include_metadata=True)
        return [m.metadata.get("text", "") for m in results.matches if m.metadata]


# ── Public async API ────────────────────────────────────────────────────────

async def ingest_dir():
    """Load PDFs/MDs, embed, and upsert into Pinecone."""
    processor = PDFProcessor()
    docs = processor.load_docs(DIRECTORY)
    if not docs:
        print("No documents found in input_documents/")
        return None
    chunks = processor.split_docs(docs)
    processor.create_index(chunks)
    print(f"Ingested {len(chunks)} chunks into '{INDEX_NAME}'")
    return INDEX_NAME


def query_index(question: str) -> str:
    """Semantic search — returns relevant document chunks as a single string."""
    processor = PDFProcessor()
    chunks = processor.retrieve(question)
    if not chunks:
        return ""
    return "\n-----\n".join(chunks)
