from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from src.rag_agent.pinecone_db import index


# ----------------------------------------
# Embedding model
# ----------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# ----------------------------------------
# Connect to Pinecone vector store
# ----------------------------------------

vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings
)


# ----------------------------------------
# Search function
# ----------------------------------------

def search(query, k=3):

    results = vector_store.similarity_search_with_score(
        query,
        k=k
    )

    return results