from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.chains import RetrievalQA
from langchain_community.vectorstores import FAISS 
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()

# Step 01: Setup llm
def load_llm(api_key=None):
    # If no key is passed, the OPENAI_API_KEY environment variable is used
    key_args = {"api_key": api_key} if api_key else {}
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=512,
        **key_args
    )
    return llm

# Step 02: Setup Prompt
def set_custom_prompt():
    custom_prompt_template = """
    Use the pieces of information provided in the context to the answer user's question.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Don't provide anything out of the given context.

    Context: {context}
    Question: {question}

    Start the answer directly. No small talk please.
    """
    prompt = PromptTemplate(
        template=custom_prompt_template,
        input_variables=["context", "question"]
    )
    return prompt

# Step 03: Create chain logic wrapped in a function
def get_qa_chain(api_key=None):
    DB_PATH = "vectorstore/db_faiss"
    key_args = {"api_key": api_key} if api_key else {}
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small", **key_args)
    
    # Load the database
    db = FAISS.load_local(DB_PATH, embedding_model, allow_dangerous_deserialization=True)

    # Build the QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=load_llm(api_key),
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={'k': 3}),
        return_source_documents=True,
        chain_type_kwargs={
            'prompt': set_custom_prompt()
        }
    )
    return qa_chain

# Step 04: Chat memory - rewrite a follow-up question into a standalone question
def condense_question(question, history, api_key=None):
    # `history` is a list of {'role': ..., 'content': ...} messages from the current chat
    if not history:
        return question

    condense_prompt = PromptTemplate.from_template(
        """
        Given the conversation below and a follow-up question, rewrite the follow-up
        question so that it can be understood on its own, without the conversation.
        Return only the rewritten question.

        Conversation:
        {history}

        Follow-up question: {question}

        Standalone question:
        """
    )
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-6:]
    )
    chain = condense_prompt | load_llm(api_key) | StrOutputParser()
    return chain.invoke({"history": history_text, "question": question}).strip() or question
