import os
import streamlit as st
from dotenv import load_dotenv
from htmlTemplates import css, bot_template, user_template
from utils import (
    # get_qdrant_vectorstore, 
    get_conversation_chain, 
    display_database_info,
    get_reranked_qdrant_retriever,
)


def handle_userinput(user_question):
    """
    Handle user input and generate response using the conversation chain.
    """
    if st.session_state.conversation is None:
        st.error("Please connect to the database first!")
        return
        
    try:
        response = st.session_state.conversation({'question': user_question})
        st.session_state.chat_history = response['chat_history']

        # Group messages into pairs: (user, bot)
        pairs = [
            (st.session_state.chat_history[i], st.session_state.chat_history[i + 1])
            for i in range(0, len(st.session_state.chat_history) - 1, 2)
        ]

        # Reverse the pairs and display user first, then bot
        for user_msg, bot_msg in reversed(pairs):
            st.write(user_template.replace("{{MSG}}", user_msg.content), unsafe_allow_html=True)
            st.write(bot_template.replace("{{MSG}}", bot_msg.content), unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Error processing your question: {str(e)}")


def main():
    load_dotenv()

    st.set_page_config(
        page_title="RAG with your PDF Knowledge Base",
        page_icon="🤖",
        layout="wide"
    )
    st.write(css, unsafe_allow_html=True)

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if "vectorstore_connected" not in st.session_state:
        st.session_state.vectorstore_connected = False

    # Main header
    st.header("🤖 RAG Chat with PDF Knowledge Base")
    # st.markdown("Ask questions about the documents in your knowledge base!")

    # Sidebar for database connection
    with st.sidebar:
        st.subheader("📚 Knowledge Base")
        
        st.markdown("---")

        if not st.session_state.vectorstore_connected:
            # Show RED connect button before connection
            if st.button("🔌 Connect to Knowledge Base", type="primary"):
                with st.spinner("Connecting to Qdrant database..."):
                    try:
                        # vectorstore = get_qdrant_vectorstore() # Naive RAG
                        vectorstore = get_reranked_qdrant_retriever() # Reranked RAG
                        st.session_state.conversation = get_conversation_chain(vectorstore)
                        st.session_state.vectorstore_connected = True
                        st.success("✅ Successfully connected to knowledge base!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
                        st.session_state.vectorstore_connected = False
        else:
            # Show GREEN button after connection (not clickable)
            st.markdown(
                """
                <div style="text-align:center;">
                    <button disabled style="
                        background-color: #28a745;
                        color: white;
                        border: none;
                        padding: 0.5rem 1rem;
                        border-radius: 0.5rem;
                        font-size: 1rem;
                        width: 100%;
                        cursor: default;
                    ">
                        🟢 Connected to Knowledge Base
                    </button>
                </div>
                """,
                unsafe_allow_html=True
            )  

            # Display database info
            display_database_info()             

    # # Main chat interface
    # if st.session_state.vectorstore_connected:
    #     st.success("🟢 Knowledge base connected - Ready to answer questions!")
    # else:
    #     st.warning("🟡 Please connect to the knowledge base first using the sidebar")

    # Chat input
    user_question = st.text_input(
        "💬 Ask a question about your documents:",
        placeholder="What would you like to know?",
        disabled=not st.session_state.vectorstore_connected
    )
    
    if user_question and st.session_state.conversation:
        handle_userinput(user_question)

    # Display chat history if exists
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Conversation History")


if __name__ == '__main__':
    main()
