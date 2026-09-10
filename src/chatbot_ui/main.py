# src/chatbot_ui/main.py
import os
import re
from html import escape
from io import BytesIO
import streamlit as st
from pathlib import Path
import requests
from htmlTemplates import css, bot_template, user_template

# API_URL = "http://localhost:8000"  # Update for production (e.g., hosted backend)
API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_app_version() -> str:
    """
    Returns the app version from version.txt.
    Tries multiple locations to work both locally and inside Docker.
    """    
    candidate_paths = [
        Path(__file__).resolve().parent / "version.txt",        # next to this file
        Path(__file__).resolve().parent.parent / "version.txt", # parent folder
        Path("version.txt"),                                    # working directory
        Path("/app/version.txt"),                                # Docker container standard path
    ]

    for path in candidate_paths:
        try:
            if path.is_file():
                return path.read_text().strip()
        except Exception:
            continue

    # 3) As a last resort, walk up from current file
    p = Path(__file__).resolve().parent
    for _ in range(6):
        candidate = p / "version.txt"
        if candidate.is_file():
            return candidate.read_text().strip()
        p = p.parent

    return "unknown"


# Function to get document titles from the backend API
def get_document_titles():
    try:
        endpoint = "papers" if st.session_state.get("corpus") == "arxiv" else "documents"
        response = requests.get(f"{API_URL}/{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to get document titles: {e}")
        return None
    

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
        
        # response = requests.post(f"{API_URL}/rag2", json={"query": question}, headers=headers)
        payload = {
            "query": question,
            "generation_model": st.session_state.generation_model,
            "mode": st.session_state.rag_mode,
            "corpus": st.session_state.corpus,
            "corpus_snapshot": st.session_state.get("corpus_snapshot") if st.session_state.corpus == "arxiv" else None,
        }

        response = requests.post(f"{API_URL}/rag2", json=payload, headers=headers, timeout=180)
        if response.status_code in (409, 503):
            st.warning(response.json().get("detail", "Corpus unavailable"))
            return None
        response.raise_for_status()
        
        # Check if the backend set a new session_id and store it
        new_session_id = get_session_id_from_response(response)
        if new_session_id:
            st.session_state.session_id = new_session_id

        result = response.json()
        if result.get("corpus_snapshot"):
            st.session_state.corpus_snapshot = result["corpus_snapshot"]
        return result
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

    # Initialize session state variables
    if "full_conversation" not in st.session_state:
        st.session_state.full_conversation = []   # all turns for display
    if "backend_memory" not in st.session_state:
        st.session_state.backend_memory = []      # summarized memory view
    if "session_id" not in st.session_state:  
        st.session_state.session_id = "" # Use an empty string instead of None   

    st.header("🤖 RAG Chat with PDF Knowledge Base")

    with st.sidebar:
        st.subheader("📚 Knowledge Base")
        st.selectbox("Corpus", ["uploads", "arxiv"], key="corpus",
                     format_func=lambda value: "Uploaded PDFs" if value == "uploads" else "arXiv star clusters")
        st.radio("Retrieval mode", ["vanilla", "hybrid"], key="rag_mode",
                 format_func=lambda value: "Vanilla — dense retrieval" if value == "vanilla" else "Hybrid — fusion + reranking")
        st.caption("Both presets retrieve evidence directly; neither uses the intent router or a knowledge graph.")
        if st.session_state.corpus == "arxiv":
            st.caption("Default scope: astro-ph.GA + star-cluster terms. Change scope in backend configuration.")
            if st.button("Refresh arXiv corpus / reset comparison"):
                st.session_state.pop("corpus_snapshot", None)
                st.session_state.session_id = ""
                st.session_state.full_conversation = []
                st.session_state.backend_memory = []
            if st.session_state.get("corpus_snapshot"):
                st.caption(f"Corpus fingerprint: {st.session_state.corpus_snapshot}")
        st.caption("PDF uploads below are added only to the Uploaded PDFs corpus.")

        # st.markdown("---")
        # st.subheader("📊 Database Content")
        if st.button("Currently in database", use_container_width=True,
                     help="Lists the selected corpus: Uploaded PDFs or ready arXiv papers."):
            titles_data = get_document_titles()
            if titles_data:
                titles_list = titles_data.get("titles", [])
                total = titles_data.get("total_documents", 0)

                # Build the response string
                response_str = f"📚 **Total Documents:** {total}\n\n**Titles:**\n"
                if titles_list:
                    # Using a numbered list for better readability
                    for i, title in enumerate(titles_list, 1):
                        response_str += f"{i}. {title}\n"
                else:
                    response_str += "No documents found in the database."

                # Append the response to the conversation history
                st.session_state.full_conversation.append({
                    "role": "assistant",
                    "content": response_str,
                    "sources": [] # No sources for this type of response
                })

        st.markdown("---")
        st.subheader("➕ Ingest Your Own PDFs")

        # Add a radio button to choose the input method
        ingestion_method = st.radio(
            "Select ingestion method:",
            ("Upload from Local", "Upload from URL"),
            key="ingestion_method"
        )

        # Display the appropriate widget based on the selection
        uploaded_files = []
        # pdf_url = ""

        if ingestion_method == "Upload from Local":
            uploaded_files = st.file_uploader(
                "Upload one or more PDF documents",
                type="pdf",
                accept_multiple_files=True,
                key="local_uploader"
            )
            ingest_button_label = "Ingest Files"
        else: # "Upload from URL"
            pdf_urls_text = st.text_area(
                "Paste PDF URLs here (one per line):",            
                key="url_input",
                placeholder="https://example.com/doc1.pdf\nhttps://example.com/doc2.pdf"
            )
            ingest_button_label = "Ingest from URL"

        # Ingestion button and logic
        ingest_button = st.button(ingest_button_label, use_container_width=True)

        if ingest_button:
            if ingestion_method == "Upload from Local" and uploaded_files:

                with st.spinner("Ingesting documents... This may take a few minutes."):
                    files_to_send = [
                        ("files", (uploaded_file.name, uploaded_file, "application/pdf"))
                        for uploaded_file in uploaded_files
                    ]
                    try:
                        response = requests.post(f"{API_URL}/ingest", files=files_to_send, timeout=300)
                        response.raise_for_status()
                        st.success("✅ Documents ingested successfully!")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Failed to ingest documents: {e}")

            elif ingestion_method == "Upload from URL" and pdf_urls_text: #pdf_url:

                with st.spinner("Downloading and ingesting document from URL... This may take a few minutes."):
                    # Split the string of URLs by newlines
                    urls_list = [url.strip() for url in pdf_urls_text.split('\n') if url.strip()]
                    
                    if not urls_list:
                        st.error("Please enter at least one valid URL.")
                        st.stop()

                    try:
                        files_to_send = []
                        for url in urls_list:
                            # Download the file from the URL
                            response = requests.get(url, timeout=300)
                            response.raise_for_status()
                            
                            file_content = BytesIO(response.content)
                            filename = os.path.basename(url) or 'downloaded_pdf.pdf'
                            
                            files_to_send.append(("files", (filename, file_content, "application/pdf")))
                        
                        # Post all files to the existing backend endpoint
                        backend_response = requests.post(
                            f"{API_URL}/ingest",
                            files=files_to_send,
                            timeout=300
                        )
                        backend_response.raise_for_status()

                        st.success("✅ Document ingested successfully from URL!")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Failed to ingest URL: {e}")

        st.markdown("---")
        st.subheader("⚙️ Generation Model")

        # Mapping of internal value -> user-friendly label
        model_labels = {
            "openai/gpt-oss-120b":  "gpt-oss-120b (fast, reasoning)", 
            "openai/gpt-oss-20b":  "gpt-oss-20b (fastest, some reasoning)", 
            "llama-3.3-70b-versatile":  "llama-3.3-70b (fast but succinct)",            
            "gpt-4.1-nano": "gpt-4.1-nano (fast)",
            "gpt-4.1-mini": "gpt-4.1-mini (balanced)",
            "gpt-5-nano":  "gpt-5-nano (slow, reasoning)",            
        }

        # Let the user see the descriptive labels
        selected_label = st.selectbox(
            "Select generation model",
            options=list(model_labels.values()),
            index=1, # index of default selection
            key="generation_model_label"
        )

        # Map back to the actual model name
        # e.g., "gpt-4.1-nano (very fast)" → "gpt-4.1-nano"
        st.session_state.generation_model = next(
            key for key, val in model_labels.items() if val == selected_label
        )        

        # st.markdown("---")
        # ✅ Show version here
        st.caption(f"App version: {get_app_version()}")


    comparison_key = (st.session_state.corpus, st.session_state.rag_mode, st.session_state.generation_model)
    if st.session_state.get("comparison_key") != comparison_key:
        st.session_state.full_conversation = []
        st.session_state.backend_memory = []
        st.session_state.session_id = ""
        st.session_state.comparison_key = comparison_key

    with st.form("question_form"):
        question = st.text_input(
            "💬 Ask a question:",
            placeholder="e.g. Compare methods for measuring star-cluster ages across papers.",
            key="user_question"
        )
        submitted = st.form_submit_button("Ask")

    if submitted and question.strip():
        result = ask_question_to_backend(question)
        if result:
            # Update frontend full conversation (append user + assistant)
            st.session_state.full_conversation.append({"role": "user", "content": question})
            # st.session_state.full_conversation.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources", [])})
            st.session_state.full_conversation.append({
                "role": "assistant", 
                "content": result["answer"], 
                "sources": result.get("sources", []),
                "images": result.get("images", [])
            })            

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

                    # 1. Logic for text/source processing
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
                            reference = f"- {escape(authors)} ({escape(str(year))}). <em>{escape(title)}</em>{pages_str}"
                            source_url = src.get("source_url") or ""
                            if source_url.startswith("https://arxiv.org/abs/"):
                                label = f"arXiv:{src.get('arxiv_id')}v{src.get('paper_version')}"
                                reference += f' — <a href="{escape(source_url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>'
                            sources_list.append(reference)

                        
                        # sources_md = "\n\n---\n**Sources:**\n" + "\n".join(sources_list)                   

                        # # Convert Markdown list to a basic HTML unordered list
                        # sources_items_html = "".join([f"<li>{item[2:].strip()}</li>" for item in sources_list])
                        # sources_md = "<hr><strong>Sources:</strong><ul>" + sources_items_html + "</ul>"

                        # Convert Markdown list to a basic HTML unordered list
                        # Note: We strip the leading '- ' before wrapping in <li>
                        sources_items_html = "".join([f"<li>{item[2:].strip()}</li>" for item in sources_list])
                        
                        # Use proper HTML tags for the source section
                        sources_md_html = "<hr style='margin: 10px 0; border: 0; border-top: 1px solid rgba(0,0,0,.1);'><strong>Sources:</strong><ul>" + sources_items_html + "</ul>"
                        
                        # full_content += sources_md
                        full_content += sources_md_html


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



                    # 1. Convert bolding (**text**) to HTML <strong>
                    # This must be done BEFORE step 3, as the dash is part of the list item
                    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', full_content)
                    
                    # 2. Convert bullet list dash character to the HTML list structure
                    # Find lines starting with a dash and a space, and convert them to <li> tags
                    html_content = re.sub(r'\n- (.*)', r'<ul><li>\1</li></ul>', html_content)
                    
                    # Optional: Clean up lists that might span multiple lines if the LLM output is inconsistent
                    # For simple lists, the previous step is usually sufficient. 
                    
                    # 3. Replace all remaining newlines with HTML line breaks
                    # We do this last to handle paragraph breaks in the main text
                    html_content = html_content.replace('\n', '<br>') 
                    
                    
                    # 2. Display the Bot Bubble
                    # --- DISPLAY FINAL HTML CONTENT ---
                    st.write(bot_template.replace("{{MSG}}", html_content), unsafe_allow_html=True)
                    # st.markdown(full_content)

                    # 3. Display Figures immediately after the bubble
                    # Check if the API response included images (figures)
                    # retrieve images from the CURRENT message being looped over
                    images = msg.get("images", [])

                    if images:
                        # st.markdown("#### 🖼️ Relevant Figures")
                        # Use a custom div for the header to style it via CSS
                        st.markdown('<p class="assistant-fig-header">🖼️ Relevant Figures</p>', unsafe_allow_html=True)                        
                        
                        # Display images in a responsive grid (2 columns)
                        # Use a grid (2 columns)
                        cols = st.columns(2)
                        for i, img in enumerate(images):
                            with cols[i % 2]:
                                # IMPORTANT: 'img["url"]' is already an absolute URL 
                                # from the backend, so we use it directly.
                                st.image(
                                    img['url'], 
                                    caption=f"Fig from page {img.get('page', '?')}: {img['caption']}",
                                    use_container_width=True
                                )
                                # Optional: Additional metadata in an expander
                                with st.expander("📄 Source Info"):
                                    st.write(f"**Paper:** {img.get('file_title', 'Unknown')}")
                                    st.write(f"**Full Caption:** {img.get('caption')}")

    # Optional: show backend’s truncated memory view
    if st.session_state.backend_memory:
        st.markdown("---")
        st.subheader("🧠 Backend Memory View (summarized + truncated)")

        for msg in st.session_state.backend_memory:
            st.markdown(f"**{msg['role'].capitalize()}:** {msg['content']}")


if __name__ == "__main__":
    main()
