import os
import pymupdf  # this is the official PyMuPDF package
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------- Configuration ----------
# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/Thesis_de_Meulenaer.pdf"

OUTPUT_FILE = "structured_output.md"
MODEL = "llama-3.1-8b-instant" #"llama-3.3-70b-versatile"
# MODEL = "llama-3.3-70b-versatile"
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

#     prompt = f"""
# You are an intelligent assistant helping to parse scientific papers.

# Here is the **full text** of a scientific paper. Please segment the content into chunks that correspond to **logical sections** (e.g., Abstract, Introduction, Methods, Results, and so on). 

# For each chunk, please return the **entire text of the section**, not just an extract.

# -- BEGIN PAPER TEXT ---
# {text}
# --- END PAPER TEXT ---
# """
    
#     # Detect sections and sub-sections
#     prompt = f"""
# You are an intelligent assistant helping to parse scientific papers.

# Here is the **full text** of a scientific paper. Please return a list of **logical sections** from the PDF as a string that could easily be parsed using Python.

# Please be concise: **just** return the section and sub-sections titles, one per line, without any additional text or formatting, and without adding any comment.

# Here follows the scientific paper text:

# -- BEGIN PAPER TEXT ---
# {text}
# --- END PAPER TEXT ---
# """    




#     # Detect sections and sub-sections
#     prompt = f"""
# You are an intelligent assistant helping to parse scientific PhD thesis PDF documents.

# Here is the **full text** of such PhD thesis. Please return a list of **logical sections** from the PDF as a string that could easily be parsed using Python.

# Please be concise: **just** return the document title, the section and sub-sections titles, without any additional text or formatting, and without adding any comment.

# Please follow this example for the output format:

# Title: The accuracy of integrated star cluster parameters.
# Introduction: Motivation, aims of the study, and paper summary.
# Chapter 1: Star Cluster Models
#    1.1. Failure and need of more elaborated models
#    1.1.1. The Simple Stellar Population models: deﬁnition
#    1.1.2. The degeneracy problem
#    1.1.3. The stochasticity problem
#    1.2. Stochastically sampled star cluster models
# Chapter 2: Deriving the Cluster Parameters
#    2.1. The method of star cluster parameters derivation
#    2.2. Improvement on the derivation of parameters
# ...
# Conclusions.
# References.

# Here follows the PhD thesis text:

# -- BEGIN PAPER TEXT ---
# {text}
# --- END PAPER TEXT ---
# """ 
    

    
    # Capture the abstract
    prompt = f"""
You are an intelligent assistant skilled at extracting structured Table of Contents (TOC) from scientific documents, particularly PhD theses.

Your task is to identify all logical sections and subsections from the provided text, along with their precise start and end page numbers. The text provided will be the initial pages of a PhD thesis, where the Table of Contents is typically located.

Return the extracted TOC as a JSON array of objects. Each object in the array should represent a section or subsection and contain the following fields:
- `title`: The exact title of the section or subsection.
- `level`: An integer representing the hierarchical level (e.g., 1 for "Chapter 1", 2 for "1.1.", 3 for "1.1.1."). The main document title, if clearly identifiable from the TOC section, should have a level of 0.
- `start_page`: The page number where this section officially begins, as indicated in the TOC.
- `end_page`: The page number where this section officially ends. This should be the `start_page` of the *next* section listed in the TOC. If it's the very last section listed, its `end_page` should be the last page of the entire document (you will need to provide the total document pages separately to the LLM if not inherent in the TOC text itself, or specify a placeholder like "DOCUMENT_END").

Please only output the JSON array. Do not include any other text, comments, or explanations.

Example of desired JSON output format (assuming 'DOCUMENT_END' for the final page):

```json
[
  {
    "title": "The accuracy of integrated star cluster parameters",
    "level": 0,
    "start_page": 1,
    "end_page": 5
  },
  {
    "title": "Introduction: Motivation, aims of the study, and paper summary",
    "level": 1,
    "start_page": 6,
    "end_page": 10
  },
  {
    "title": "Chapter 1: Star Cluster Models",
    "level": 1,
    "start_page": 11,
    "end_page": 30
  },
  {
    "title": "1.1. Failure and need of more elaborated models",
    "level": 2,
    "start_page": 12,
    "end_page": 20
  },
  {
    "title": "1.1.1. The Simple Stellar Population models: deﬁnition",
    "level": 3,
    "start_page": 13,
    "end_page": 15
  },
  {
    "title": "1.1.2. The degeneracy problem",
    "level": 3,
    "start_page": 16,
    "end_page": 18
  },
  {
    "title": "1.1.3. The stochasticity problem",
    "level": 3,
    "start_page": 19,
    "end_page": 20
  },
  {
    "title": "1.2. Stochastically sampled star cluster models",
    "level": 2,
    "start_page": 21,
    "end_page": 30
  },
  {
    "title": "Chapter 2: Deriving the Cluster Parameters",
    "level": 1,
    "start_page": 31,
    "end_page": 55
  },
  {
    "title": "2.1. The method of star cluster parameters derivation",
    "level": 2,
    "start_page": 32,
    "end_page": 40
  },
  {
    "title": "2.2. Improvement on the derivation of parameters",
    "level": 2,
    "start_page": 41,
    "end_page": 55
  },
  {
    "title": "Conclusions",
    "level": 1,
    "start_page": 56,
    "end_page": 60
  },
  {
    "title": "References",
    "level": 1,
    "start_page": 61,
    "end_page": "DOCUMENT_END"
  }
]

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