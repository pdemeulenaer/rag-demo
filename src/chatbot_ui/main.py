
import os
import streamlit as st
import requests
from htmlTemplates import css, bot_template, user_template

# API_URL = "http://localhost:8000"  # Update for production (e.g., hosted backend)
API_URL = os.getenv("API_URL", "http://localhost:8000")


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


# def connect_to_backend():
#     try:
#         response = requests.post(f"{API_URL}/connect")
#         response.raise_for_status()
#         return True
#     except Exception as e:
#         st.error(f"❌ Backend connection failed: {e}")
#         return False
         

def ask_question_to_backend(question):
    try:
        headers = {"Content-Type": "application/json"}
        # Include the session_id cookie if it exists in the session state
        # if "session_id" in st.session_state:
        if st.session_state.session_id:
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

    # Always clear session state on hard refresh
    if st.session_state.get("init_done") is None:
        st.session_state.clear()
        st.session_state.init_done = True

    # Initialize session state
    # if "connected" not in st.session_state:
    #     st.session_state.connected = False
    if "full_conversation" not in st.session_state:
        st.session_state.full_conversation = []   # all turns for display
    if "backend_memory" not in st.session_state:
        st.session_state.backend_memory = []      # summarized memory view
    if "session_id" not in st.session_state:
        # st.session_state.session_id = None     
        st.session_state.session_id = "" # Use an empty string instead of None   

    st.header("🤖 RAG Chat with PDF Knowledge Base")

    with st.sidebar:
        st.subheader("📚 Knowledge Base")

        # if not st.session_state.connected:
        #     if connect_to_backend():
        #         st.session_state.connected = True
        #         st.success("✅ Connected to backend")
        #         st.rerun()
        # else:
        #     st.success("🟢 Connected to Knowledge Base")
    # st.session_state.connected = True
        st.success("🟢 Connected to Knowledge Base")
        st.info("The knowledge base is pre-loaded from a set of astronomy papers in PDF format.")

    question = st.text_input(
        "💬 Ask a question:",
        placeholder="e.g. How to derive the parameters of star clusters using broad-band photometry?",
        # disabled=not st.session_state.connected,
        key="user_question"
    )

    if question:
        result = ask_question_to_backend(question)
        if result:
            # Update frontend full conversation (append user + assistant)
            st.session_state.full_conversation.append({"role": "user", "content": question})
            st.session_state.full_conversation.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources", [])})

            # Store backend's truncated/summarized memory separately
            if "chat_history" in result:
                st.session_state.backend_memory = result["chat_history"]

    # Show full conversation (frontend memory)
    if st.session_state.full_conversation:
        st.markdown("---")
        st.subheader("💬 Full Conversation (Frontend)")

        # Process in pairs: user + assistant
        turns = [
            st.session_state.full_conversation[i:i+2]
            for i in range(0, len(st.session_state.full_conversation), 2)
        ]

        # Reverse order so newest turn appears first
        for turn in reversed(turns):
            for msg in turn:
                if msg["role"] == "user":
                    st.write(user_template.replace("{{MSG}}", msg["content"]), unsafe_allow_html=True)
                elif msg["role"] == "assistant":
                    # Combine the answer and sources into a single markdown string
                    full_content = msg["content"]
                    if "sources" in msg and msg["sources"]:
                        sources_list = []
                        for src in msg["sources"]:
                            authors = src.get("authors") or "Unknown author"
                            if isinstance(authors, list):
                                authors = ", ".join(authors)
                            year = src.get("year") or "n.d."
                            title = src.get("title") or "Untitled"
                            # sources_list.append(f"- {authors} ({year}). *{title}*")
                            pages = src.get("page")  # this is a list of ints
                            pages_str = f" pp. {', '.join(map(str, pages))}" if pages else ""
                            sources_list.append(f"- {authors} ({year}). *{title}*{pages_str}")

                        
                        sources_md = "\n\n---\n**Sources:**\n" + "\n".join(sources_list)
                        full_content += sources_md
                    
                    # if "sources" in msg and msg["sources"]:
                    #     # Aggregate sources by (authors, title, year)
                    #     aggregated = {}
                    #     for src in msg["sources"]:
                    #         authors = src.get("authors") or ["Unknown author"]
                    #         title = src.get("title") or "Untitled"
                    #         year = src.get("year") or "n.d."
                    #         pages = src.get("page")  # could be int or list
                            
                    #         key = (tuple(authors), title, year)
                    #         if key not in aggregated:
                    #             aggregated[key] = set()
                            
                    #         if pages:
                    #             if isinstance(pages, list):
                    #                 aggregated[key].update(pages)
                    #             else:
                    #                 aggregated[key].add(pages)
                        
                    #     # Build markdown list
                    #     sources_list = []
                    #     for (authors_tuple, title, year), pages_set in aggregated.items():
                    #         authors_str = ", ".join(authors_tuple)
                    #         pages_str = ", ".join(str(p) for p in sorted(pages_set))
                    #         if pages_str:
                    #             sources_list.append(f"- {authors_str} ({year}). *{title}* — pages: {pages_str}")
                    #         else:
                    #             sources_list.append(f"- {authors_str} ({year}). *{title}*")
                        
                    #     sources_md = "\n\n---\n**Sources:**\n" + "\n".join(sources_list)
                    #     full_content += sources_md

                    st.write(bot_template.replace("{{MSG}}", full_content), unsafe_allow_html=True)




    # Optional: show backend’s truncated memory view
    if st.session_state.backend_memory:
        st.markdown("---")
        st.subheader("🧠 Backend Memory View (summarized + truncated)")

        for msg in st.session_state.backend_memory:
            st.markdown(f"**{msg['role'].capitalize()}:** {msg['content']}")


if __name__ == "__main__":
    main()
