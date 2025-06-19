import os
import pymupdf  # this is the official PyMuPDF package
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------- Configuration ----------
PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
OUTPUT_FILE = "structured_output.md"
MODEL = "llama-3.1-8b-instant" #"llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
assert GROQ_API_KEY, "❌ GROQ_API_KEY is not set in environment variables."

# ---------- Setup Groq Client ----------
client = Groq(api_key=GROQ_API_KEY)

# ---------- Functions ----------
def extract_pdf_text(pdf_path):
    text = ""
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def call_llm_for_structured_chunks(text):
#     prompt = f"""
# You are an intelligent assistant helping to parse scientific papers.

# Here is the **full text** of a scientific paper. Please do the following:
# - Segment the content into chunk that correspond to **logical sections** (e.g., Abstract, Introduction, Methods, Results, etc.). The section should contain the whole section text. If the section text is larger than 2000 tokens, then it could be splitted in multiple chunks.
# - Each chunk should contain:

#     - `title`: the paper title
#     - `authors`: the authors of the paper
#     - `section`: current section name (e.g. "Introduction")
#     - `previous_section`: name of the previous section (if any)
#     - `next_section`: name of the next section (if any)
#     - `summary`: a 1–2 sentence summary of the chunk
#     - `keywords`: list of any named entities, technique names, acronyms, chemical or biological terms, datasets, or scientific keywords from this section
#     - `text`: the **section content** in Markdown.

# Here after is the entire input text: 

# -- BEGIN PAPER TEXT ---
# {text}
# --- END PAPER TEXT ---
# """

    prompt = f"""
You are an intelligent assistant helping to parse scientific papers.

Here is the **full text** of a scientific paper. Please segment the content into chunks that correspond to **logical sections** (e.g., Abstract, Introduction, Methods, Results, and so on). 

For each chunk, please return the **entire text of the section**, not just an extract.

-- BEGIN PAPER TEXT ---
{text}
--- END PAPER TEXT ---
"""

    print("🧠 Calling Groq LLM to segment and annotate...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

# ---------- Run Pipeline ----------
if __name__ == "__main__":
    print(f"📄 Extracting text from: {PDF_PATH}")
    raw_text = extract_pdf_text(PDF_PATH)

    print("🚀 Sending text to Groq for processing...")
    markdown_output = call_llm_for_structured_chunks(raw_text)

    with open("structured_output_raw.md", "w", encoding="utf-8") as f:
        f.write(raw_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(markdown_output)

    print(f"✅ Markdown output written to: {OUTPUT_FILE}")