import streamlit as st
import requests
from htmlTemplates import css, bot_template, user_template

API_URL = "http://localhost:8000"  # Update for production (e.g., hosted backend)

def connect_to_backend():
    try:
        response = requests.post(f"{API_URL}/connect")
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ Backend connection failed: {e}")
        return False

# def ask_question_to_backend(question):
#     try:
#         # response = requests.post(f"{API_URL}/rag", json={"question": question})
#         response = requests.post(f"{API_URL}/rag2", json={"question": question})
#         response.raise_for_status()
#         return response.json()
#     except Exception as e:
#         st.error(f"❌ Failed to get response: {e}")
#         return None
    
def ask_question_to_backend(question):
    try:
        # Change 'question' to 'query' to match the RAGRequest model
        response = requests.post(f"{API_URL}/rag2", json={"query": question})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ Failed to get response: {e}")
        return None    

# def main():
#     st.set_page_config(page_title="RAG Chat", page_icon="🤖", layout="wide")
#     st.write(css, unsafe_allow_html=True)

#     if "connected" not in st.session_state:
#         st.session_state.connected = False
#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []

#     st.header("🤖 RAG Chat with PDF Knowledge Base")

#     with st.sidebar:
#         st.subheader("📚 Knowledge Base")

#         if not st.session_state.connected:
#             # if st.button("🔌 Connect to Knowledge Base", type="primary"):
#             if connect_to_backend():
#                 st.session_state.connected = True
#                 st.success("✅ Connected to backend")
#                 st.rerun()
#         else:
#             st.success("🟢 Connected to Knowledge Base")

#     question = st.text_input(
#         "💬 Ask a question:",
#         placeholder="e.g. How to derive the parameters of star clusters using broad-band photometry?",
#         disabled=not st.session_state.connected
#     )

#     if question:
#         result = ask_question_to_backend(question)
#         if result:
#             st.session_state.chat_history = result["chat_history"]

#     if st.session_state.chat_history:
#         st.markdown("---")
#         st.subheader("💬 Conversation History")
#         pairs = [
#             (st.session_state.chat_history[i], st.session_state.chat_history[i + 1])
#             for i in range(0, len(st.session_state.chat_history) - 1, 2)
#         ]
#         for user_msg, bot_msg in reversed(pairs):
#             st.write(user_template.replace("{{MSG}}", user_msg["content"]), unsafe_allow_html=True)
#             st.write(bot_template.replace("{{MSG}}", bot_msg["content"]), unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="RAG Chat", page_icon="🤖", layout="wide")
    st.write(css, unsafe_allow_html=True)

    # Initialize session state variables unconditionally at the beginning
    if "connected" not in st.session_state:
        st.session_state.connected = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

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
        disabled=not st.session_state.connected
    )

    if question:
        result = ask_question_to_backend(question)
        if result:
            # The backend is returning the FULL chat_history, so we just update the state
            st.session_state.chat_history = result["chat_history"]

    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Conversation History")
        
        # This loop correctly displays all messages in the history
        for msg in reversed(st.session_state.chat_history):
            if msg["role"] == "user":
                st.write(user_template.replace("{{MSG}}", msg["content"]), unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                st.write(bot_template.replace("{{MSG}}", msg["content"]), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
