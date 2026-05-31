# Writer's Story Companion

Writer’s Story Companion is an AI-powered\ fiction assistant designed to help writers explore and continue their stories through intelligent “what-if” scenarios and context-aware plot generation.

Large novels can easily exceed the context window of an LLM, making it impossible to send the entire story directly to the model. To solve this, the application stores uses RAG which retrieves only the most relevant narrative context for each user query.

## Live Demo

### Backend API (FastAPI): [https://your-fastapi-space.hf.space](https://paru-73-Story-companion.hf.space)

#### Live link: https://storyweave-ai-scribe.lovable.app/

## Features

- Multi-story support
- Upload PDF, DOCX, TXT, PPTX story files
- Persistent vector database using ChromaDB
- Context-aware story continuation
- Separate chat history for each story
- Retrieval-Augmented Generation (RAG)
- Gemini-powered creative responses
- Persistent sessions using JSON storage

## Tech Stack

- **Backend:** FastAPI, LangChain, ChromaDB, HuggingFace Embeddings, Gemini API

- **Embeddings Model:** `all-MiniLM-L6-v2`

## How it Works

**1. Upload Story Documents**

Users upload story files through the Streamlit sidebar.
Supported formats:
- PDF
- DOCX
- TXT
- PPTX

**2. Document Processing**

The backend:
- loads documents
- splits them into chunks
- generates embeddings
- stores them in ChromaDB

**3. Retrieval-Augmented Generation (RAG)**

When a user asks a question:
- relevant chunks are retrieved from ChromaDB
- previous story continuation is added
- Gemini generates the next continuation

**4. Persistent Story Memory**

Each story has:
- its own vector database
- its own chat sessions
- its own retriever chain


    
