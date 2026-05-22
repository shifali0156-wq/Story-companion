import streamlit as st
import requests
import uuid

BASE_URL = "https://paru-73-Story-companion.hf.space"

st.set_page_config(page_title="Writer's Story Companion", layout="wide")

st.title("RAG Chatbot (Multi-Document)")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


st.sidebar.header("Documents")

status_res = requests.get(f"{BASE_URL}/status")
status_data = status_res.json()

current_chain = status_data["chain_ready"]
docs = status_data["documents"]

if current_chain:
    st.sidebar.success("Documents already processed")
    for doc in docs:
        st.sidebar.write(f"📄 {doc}")
else:
    st.sidebar.warning("No documents uploaded yet")
    uploaded_files = st.sidebar.file_uploader(
        "Upload files (PDF, DOCX, TXT, PPTX)",
        accept_multiple_files=True
    )
    if st.sidebar.button("Process Documents"):
        if not uploaded_files:
            st.sidebar.warning("Upload files first")
        else:
            files = []
            for file in uploaded_files:
                files.append(
                    ("files", (file.name, file.getvalue(), file.type))
                )
            res = requests.post(
                f"{BASE_URL}/uploading_doc",
                files=files
            )
            if res.status_code == 200:
                st.sidebar.success("Documents processed!")
                st.rerun()
            else:
                st.sidebar.error(res.text)

st.subheader("Chat with your documents")

user_input = st.chat_input("Ask something...")

if user_input:
    st.session_state.messages.append(("user", user_input))
    res = requests.post(
        f"{BASE_URL}/chat",
        json={
            "question": user_input,
            "session_id": st.session_state.session_id
        }
    )

    if res.status_code == 200:
        answer = res.json()["response"]
    else:
        answer = f"Error: {res.text}"

    st.session_state.messages.append(("bot", answer))

for role, msg in st.session_state.messages:
    if role == "user":
        with st.chat_message("user"):
            st.write(msg)
    else:
        with st.chat_message("assistant"):
            st.write(msg)
