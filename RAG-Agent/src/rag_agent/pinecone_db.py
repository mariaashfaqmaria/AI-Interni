import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from src.rag_agent.splitting import split_pdf

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


pc = Pinecone(api_key=PINECONE_API_KEY)


INDEX_NAME = "rag-agent-index"

EMBEDDING_DIMENSION = 384

if not pc.has_index(INDEX_NAME):

    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

    print("Pinecone index created!")

else:

    print("Pinecone index already exists!")

index = pc.Index(INDEX_NAME)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings
)


chunks = split_pdf()

print("Chunks received:", len(chunks))



vector_store.add_documents(
    documents=chunks
)

print("All chunks successfully stored in Pinecone!")