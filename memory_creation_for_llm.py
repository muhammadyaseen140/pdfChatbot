# memory_creation_for_llm.py
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import os
import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)
load_dotenv()

DATA_PATH = "data/"
DB_PATH = "vectorstore/db_faiss"

def load_pdf_files(data):
    loader = DirectoryLoader(data, glob='*.pdf', loader_cls=PyPDFLoader)
    return loader.load()

def create_chunks(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return text_splitter.split_documents(extracted_data)

def get_embedding_model(api_key=None):
    # If no key is passed, the OPENAI_API_KEY environment variable is used
    key_args = {"api_key": api_key} if api_key else {}
    return OpenAIEmbeddings(model='text-embedding-3-small', **key_args)

# Wrapped in a function
def update_vectorstore(api_key=None):
    embedding_model = get_embedding_model(api_key)
    documents = load_pdf_files(data=DATA_PATH)
    
    if not documents:
        return False, "No PDFs found in the data directory."
        
    text_chunks = create_chunks(extracted_data=documents)
    
    # Create a new database and overwrite any existing one
    db = FAISS.from_documents(text_chunks, embedding_model)
    os.makedirs("vectorstore", exist_ok=True)
    db.save_local(DB_PATH)
    return True, "Knowledge base updated successfully!"
