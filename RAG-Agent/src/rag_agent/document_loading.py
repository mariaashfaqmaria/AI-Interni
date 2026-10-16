from langchain_community.document_loaders import PyPDFLoader


def load_pdf():
    pdf_path = r"C:\Users\Lenovo\RAG-Agent\data\RAG (data pdf).pdf"

    loader = PyPDFLoader(pdf_path)

    documents = loader.load()

    return documents