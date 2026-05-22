import streamlit as st
import requests

BASE_URL = "https://paru-73-Story-companion.hf.space"

st.set_page_config(
    page_title="Writer's Story Companion",
    layout="wide"
)

if "session_id" not in st.session_state:
    st.session_state.session_id = "default_user"

if "selected_story" not in st.session_state:
    st.session_state.selected_story = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.session_state.selected_story is None:

    st.title("Writer's Story Companion")

    st.markdown("### Your Story Worlds")

    # Fetch stories from backend
    try:
        res = requests.get(f"{BASE_URL}/stories")
        stories = res.json()["stories"]
    except:
        stories = []

    cols = st.columns(3)

    for idx, story in enumerate(stories):

        with cols[idx % 3]:

            with st.container(border=True):

                st.markdown(f"## 📖 {story}")

                if st.button(
                    "Open Story",
                    key=f"open_{story}"
                ):
                    st.session_state.selected_story = story
                    st.session_state.messages = []
                    st.rerun()

    st.sidebar.header("➕ Create New Story")

    story_name = st.sidebar.text_input(
        "Story Name"
    )

    uploaded_files = st.sidebar.file_uploader(
        "Upload Story Files",
        type=["pdf", "docx", "txt", "pptx"],
        accept_multiple_files=True
    )

    if st.sidebar.button("Create Story"):

        if not story_name:
            st.sidebar.warning("Please enter story name")

        elif not uploaded_files:
            st.sidebar.warning("Please upload files")

        else:

            files = []

            for file in uploaded_files:

                files.append(
                    (
                        "files",
                        (
                            file.name,
                            file.getvalue(),
                            file.type
                        )
                    )
                )

            res = requests.post(
                f"{BASE_URL}/uploading_doc/{story_name}",
                files=files
            )

            if res.status_code == 200:

                st.sidebar.success(
                    "Story uploaded successfully!"
                )

                st.rerun()

            else:

                st.sidebar.error(res.text)

else:

    selected_story = st.session_state.selected_story

    st.title(selected_story)

    if st.button("← Back to Library"):

        st.session_state.selected_story = None
        st.session_state.messages = []

        st.rerun()

    if st.session_state.messages == []:
        res = requests.get(
            f"{BASE_URL}/history/"
            f"{selected_story}/"
            f"{st.session_state.session_id}"
        )

        if res.status_code == 200:

            data = res.json()

            for item in data["messages"]:

                if item["role"] == "user":

                    st.session_state.messages.append(
                        ("user", item["message"])
                    )

                else:

                    st.session_state.messages.append(
                        ("bot", item["message"])
                    )

    for role, msg in st.session_state.messages:

        if role == "user":

            with st.chat_message("user"):
                st.write(msg)

        else:

            with st.chat_message("assistant"):
                st.write(msg)

    user_input = st.chat_input(
        "Continue your story..."
    )

    if user_input:

        st.session_state.messages.append(
            ("user", user_input)
        )

        with st.chat_message("user"):
            st.write(user_input)

        res = requests.post(
            f"{BASE_URL}/chat",
            json={
                "question": user_input,
                "session_id": st.session_state.session_id,
                "story_id": selected_story
            }
        )

        if res.status_code == 200:

            answer = res.json()["response"]

        else:

            answer = f"Error: {res.text}"

        st.session_state.messages.append(
            ("bot", answer)
        )

        with st.chat_message("assistant"):
            st.write(answer)
