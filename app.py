from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import create_history_aware_retriever
from itertools import groupby
from langchain_core.runnables import RunnablePassthrough,RunnableParallel,RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from fastapi import FastAPI, UploadFile, File
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import os
import json

load_dotenv()
key = os.getenv("GOOGLE_API_KEY")

class Upload(BaseModel):
    files:list[str]

class Query(BaseModel):
    question:str
    session_id:str
    story_id: str

app=FastAPI()

story_chains = {}

if os.path.exists("sessions.json"):
    with open("sessions.json", "r") as f:
        chat_sessions = json.load(f)
else:
    chat_sessions = {}

def load_file(file_path):
    extension=file_path.split('.')[-1].lower()
    if extension=="pdf":
        from langchain_community.document_loaders import PyPDFLoader
        loader=PyPDFLoader(file_path)
    elif extension=="docx":
        from langchain_community.document_loaders import Docx2txtLoader
        loader=Docx2txtLoader(file_path)
    elif extension=="txt":
        from langchain_community.document_loaders import TextLoader
        loader=TextLoader(file_path)
    elif extension=="pptx":
        from langchain_community.document_loaders import UnstructuredPowerPointLoader
        loader=UnstructuredPowerPointLoader(file_path)
    else:
            raise ValueError(f"Unsupported file type: {extension}")

    doc=loader.load()  
    return doc

def create_doc_ids(docs):
    documents_ids=[]
    page_groups=groupby(docs,lambda chunk:chunk.metadata["page"])
    for page, chunks in page_groups:
        for i,chunk in enumerate(chunks):
            documents_ids.append(f"{(chunk.metadata['source']).split('/')[-1]}_{page}_{i}")
    return documents_ids

def build_chain_from_doc(file_paths,db_path):
  splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
  all_docs=[]
  for file_path in file_paths:
      doc=load_file(file_path)
      chunks=splitter.split_documents(doc)
      all_docs.extend(chunks)

  chunk_ids=create_doc_ids(all_docs)
  embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

  vector_store=Chroma.from_documents(
        embedding=embeddings,
        persist_directory=db_path,
        documents=all_docs,
        ids=chunk_ids
  )
    
  retriever=vector_store.as_retriever(search_type="similarity")
  return retriever

prompt="""Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."""
contextual_query_prompt=ChatPromptTemplate.from_messages([
    ("system",prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])
    
prompt3=PromptTemplate(
    template="""You are a collaborative fiction writing co-pilot.
Your task is to generate a short and creative, merged plot continuation based on the user's provided scenario using the provided story context and the previous generated response.
Use the CONTEXT as canon truth.
STRICT RULES:
1. Stay fully consistent with established characters, relationships, tone, timeline, and world rules.
2. Write as a flowing descriptive plot idea, not bullet points.
3. Keep it compact (1–3 paragraphs).
4. Build tension, intrigue, emotional movement, or conflict.
5. Do NOT conclude the story.
6. End at an interesting open moment so the writer can continue naturally.
7. Avoid generic twists unless supported by context.
8. If context is incomplete, make only minimal logical assumptions.
STYLE:
- Cinematic
- Descriptive
- Story-like
- Suggestive rather than final
- Engaging and immersive
OUTPUT:
Return only the plot text.
CONTEXT:
{context}
WHAT-IF SCENARIO:
{question}
PREVIOUS RESPONSE:
{chat_history}""",
    input_variables=["context","question","chat_history"]
)

def format_doc(docs):
  context="\n\n".join(doc.page_content for doc in docs)
  return context

llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=key
)

parser=StrOutputParser()


def create_chain(retriever):
  parallel_chain=RunnableParallel(
        {"context":retriever | RunnableLambda(format_doc),
        "question":RunnablePassthrough(lambda x:x["input"]),
         "chat_history":RunnablePassthrough(lambda x:x["chat_history"])
         }
  )
  chain1=prompt3 | llm | parser
  return parallel_chain | chain1

def convert_history(history):
    chat_history = []
    if history==[]:
        return chat_history

    chat_history.append(HumanMessage(content=history[-1][0]))
    chat_history.append(AIMessage(content=history[-1][1]))
    print(chat_history)
    return chat_history


@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/history/{story_id}/{session_id}")
def get_history(story_id: str, session_id: str):
    if story_id not in chat_sessions:
        return {"messages": []}
    history = chat_sessions[story_id].get(
        session_id,[])
    formatted = []
    for human, ai in history:
        formatted.append({"role": "user","message": human})
        formatted.append({"role": "assistant","message": ai})

    return {"messages": formatted}

@app.get("/stories")
def get_stories():
    os.makedirs("stories", exist_ok=True)
    stories = os.listdir("stories")
    return {"stories": stories}
    
@app.post("/uploading_doc/{story_id}")
def process_document(story_id: str, files: List[UploadFile] = File(...)):
    global story_chains
    story_id=story_id.strip().replace(" ", "_")
    os.makedirs("stories", exist_ok=True)
    os.makedirs(f"stories/{story_id}/uploads", exist_ok=True)
    db_path=f"stories/{story_id}/db"
    file_paths = []
    for file in files:
        file_path = f"stories/{story_id}/uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        file_paths.append(file_path)
    retriever = build_chain_from_doc(file_paths,db_path)
    history_retriever = create_history_aware_retriever(llm,retriever,contextual_query_prompt)
    story_chains[story_id] = create_chain(history_retriever)
    return {"message": "Documents processed successfully!"}

@app.post("/chat")
def chat_with_ai(message: Query):
    global story_chains, chat_sessions
    story_id = message.story_id
    db_path = f"stories/{story_id}/db"
    if story_id not in story_chains:
        if os.path.exists(db_path):
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

            vector_store = Chroma(
                persist_directory=db_path,
                embedding_function=embeddings
            )

            retriever = vector_store.as_retriever()
            history_retriever = create_history_aware_retriever(llm,retriever,contextual_query_prompt)

            story_chains[story_id] = create_chain(history_retriever)
        else:
            return {"response": "Please upload documents first!"}

    question = message.question
    session_id = message.session_id

    if not question:
        return {"response": "Please provide a question."}

    current_chain = story_chains[story_id]

    if story_id not in chat_sessions:
        chat_sessions[story_id] = {}
    
    if session_id not in chat_sessions[story_id]:
        chat_sessions[story_id][session_id] = []

    history = chat_sessions[story_id][session_id]

    response = current_chain.invoke({"input": question,"chat_history": convert_history(history)})

    history.append((question, response))
        
    with open("sessions.json", "w") as f:
        json.dump(chat_sessions, f)

    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
