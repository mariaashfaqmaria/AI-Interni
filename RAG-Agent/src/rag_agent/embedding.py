from langchain_huggingface import HuggingFaceEmbeddings

from src.rag_agent.splitting import split_pdf


chunks = split_pdf()

print("Chunks received:", len(chunks))


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector = embeddings.embed_query(chunks[0].page_content)

print("Embedding generated successfully!")
print("Embedding dimension:", len(vector))
print("First 10 values:", vector[:10])