from dotenv import load_dotenv
load_dotenv(override=True)

from rag.rag import RAG

if __name__ == "__main__":
    rag = RAG()
    rag.launch(port=8383)