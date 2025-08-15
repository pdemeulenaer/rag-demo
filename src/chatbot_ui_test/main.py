import streamlit as st
import requests
from htmlTemplates import css, bot_template, user_template

API_URL = "http://localhost:8000"

def get_session_id_from_response(response):
    """Parses the session_id from the response cookies."""
    if 'set-cookie' in response.headers:
        cookie_header = response.headers['set-cookie']
        # Find the session_id value
        # A more robust solution might use a library like 'http.cookies'
        session_id_part = [part for part in cookie_header.split(';') if 'session_id' in part]
        if session_id_part:
            return session_id_part[0].split('=')[1]
    return None

def connect_to_backend():
    try:
        response = requests.post(f"{API_URL}/connect")
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ Backend connection failed: {e}")
        return False

def ask_question_to_backend(question):
    try:
        headers = {"Content-Type": "application/json"}
        # Include the session_id cookie if it exists in the session state
        if "session_id" in st.session_state:
            headers["Cookie"] = f"session_id={st.session_state.session_id}"
        
        response = requests.post(f"{API_URL}/rag2", json={"query": question}, headers=headers)
        response.raise_for_status()
        
        # Check if the backend set a new session_id and store it
        new_session_id = get_session_id_from_response(response)
        if new_session_id:
            st.session_state.session_id = new_session_id

        return response.json()
    except Exception as e:
        st.error(f"❌ Failed to get response: {e}")
        return None

def main():
    st.set_page_config(page_title="RAG Chat", page_icon="🤖", layout="wide")
    st.write(css, unsafe_allow_html=True)

    if "connected" not in st.session_state:
        st.session_state.connected = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    # Initialize a variable to track the last submitted question
    if "last_question" not in st.session_state:
        st.session_state.last_question = ""

    st.header("🤖 RAG Chat with PDF Knowledge Base")

    with st.sidebar:
        st.subheader("📚 Knowledge Base")

        if not st.session_state.connected:
            if connect_to_backend():
                st.session_state.connected = True
                st.success("✅ Connected to backend")
                st.rerun()
        else:
            st.success("🟢 Connected to Knowledge Base")

    question = st.text_input(
        "💬 Ask a question:",
        placeholder="e.g. How to derive the parameters of star clusters using broad-band photometry?",
        disabled=not st.session_state.connected,
        key="user_question"
    )

    # This condition correctly checks if a new question has been entered
    if question and question != st.session_state.last_question:
        st.session_state.last_question = question
        result = ask_question_to_backend(question)
        if result:
            st.session_state.chat_history = result["chat_history"]
        st.rerun()

    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Conversation History")
        
        pairs = [
            (st.session_state.chat_history[i], st.session_state.chat_history[i + 1])
            for i in range(0, len(st.session_state.chat_history) - 1, 2)
        ]
        
        for user_msg, bot_msg in reversed(pairs):
            st.write(user_template.replace("{{MSG}}", user_msg["content"]), unsafe_allow_html=True)
            st.write(bot_template.replace("{{MSG}}", bot_msg["content"]), unsafe_allow_html=True)

if __name__ == "__main__":
    main()