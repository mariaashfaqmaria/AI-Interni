from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from src.rag_agent.pinecone_db import index


# ----------------------------------------
# Embedding model
# ----------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# ----------------------------------------
# Connect to Pinecone
# ----------------------------------------

vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings
)


# ----------------------------------------
# Create retriever
# ----------------------------------------

retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)


# ----------------------------------------
# Retrieval function
# ----------------------------------------

def retrieve_documents(query):

    documents = retriever.invoke(query)

    return documents