import os
import pymupdf  # this is the official PyMuPDF package
from groq import Groq
from dotenv import load_dotenv
import json # Import json for pretty printing structured output

load_dotenv()

# ---------- Configuration ----------
# PDF_PATH is now statically defined as per user request
# Replace this with the actual path to your PDF file
PDF_PATH = "/home/philippe/Documents/vu_disertacijos/IG_Disertacija be straipsniu.pdf"

OUTPUT_FILE = "structured_output.md"
RAW_TEXT_OUTPUT_FILE = "structured_output_raw.md" # Added a separate file for raw text output
MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Assert that the API key is set
assert GROQ_API_KEY, "❌ GROQ_API_KEY is not set in environment variables."

# ---------- Setup Groq Client ----------
client = Groq(api_key=GROQ_API_KEY)

# ---------- Functions ----------
def extract_pdf_text(pdf_path, max_pages_toc=15):
    """
    Extracts text from a given PDF file, specifically the first page
    for title/author and a limited number of pages for the Table of Contents.
    This function remains as per the user's provided code for initial text extraction.

    Args:
        pdf_path (str): The file path to the PDF document.
        max_pages_toc (int): The maximum number of pages to extract text from
                             for the TOC. Defaults to 15.

    Returns:
        tuple: A tuple containing:
               - str: The text from the first page.
               - str: The concatenated text content from the specified pages for TOC.
    """
    first_page_text = ""
    toc_text = ""
    try:
        with pymupdf.open(pdf_path) as doc:
            if doc.page_count > 0:
                first_page_text = doc.load_page(0).get_text() # Get text from the first page (page index 0)

            # Iterate only up to max_pages_toc or the actual number of pages in the document
            for i, page in enumerate(doc):
                if i >= max_pages_toc:
                    break # Stop if we've processed max_pages_toc
                toc_text += page.get_text()
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return "", "" # Return empty strings on error
    return first_page_text, toc_text

def get_section_text_from_pdf(pdf_path, start_page_1_indexed, end_page_1_indexed, total_doc_pages):
    """
    NEW FUNCTION: Extracts text from a given PDF file within a specified 1-indexed page range.
    This function is designed to read the content of individual sections based on
    the start_page and end_page provided by the LLM.

    Args:
        pdf_path (str): The file path to the PDF document.
        start_page_1_indexed (int): The 1-indexed starting page number for text extraction.
        end_page_1_indexed (int or str): The 1-indexed ending page number or "DOCUMENT_END".
        total_doc_pages (int): The total number of pages in the document. Required for "DOCUMENT_END".

    Returns:
        str: The concatenated text content from the specified page range.
    """
    extracted_text = ""
    try:
        with pymupdf.open(pdf_path) as doc:
            # Adjust to 0-indexed for PyMuPDF
            start_idx = start_page_1_indexed - 1
            
            if end_page_1_indexed == "DOCUMENT_END":
                end_idx = total_doc_pages - 1
            else:
                end_idx = end_page_1_indexed - 1

            # Ensure valid range
            start_idx = max(0, start_idx)
            end_idx = min(total_doc_pages - 1, end_idx)

            if start_idx > end_idx:
                print(f"⚠️ Invalid page range for text extraction: start={start_page_1_indexed}, end={end_page_1_indexed}. Returning empty string.")
                return "" # Return empty string if range is invalid (e.g., start > end)

            for i in range(start_idx, end_idx + 1):
                page = doc.load_page(i)
                extracted_text += page.get_text()
    except Exception as e:
        print(f"❌ Error extracting text from PDF pages {start_page_1_indexed}-{end_page_1_indexed}: {e}")
        return ""
    return extracted_text

def call_llm_for_title_and_author(first_page_text):
    """
    Calls a Large Language Model (LLM) to extract the main document title and author
    from the text of the first page.

    Args:
        first_page_text (str): The text content from the first page of the document.

    Returns:
        dict: A dictionary containing 'title' and 'author' extracted by the LLM,
              or an error message if the LLM call fails.
    """
    prompt = f"""
You are an intelligent assistant skilled at extracting document titles and authors from the first page of scientific documents, particularly PhD theses.

Your task is to identify the main document title and the author(s) from the provided text, which is the content of the first page of a document.

Return the extracted information as a JSON object with the following fields:
- `document_title`: The main title of the document.
- `author`: The name of the author(s). If there are multiple authors, list them comma-separated.

Please only output the JSON object. Do not include any other text, comments, or explanations.

Example of desired JSON output format:

```json
{{
  "document_title": "The Accuracy of Integrated Star Cluster Parameters",
  "author": "John Doe"
}}
```

-- BEGIN FIRST PAGE TEXT ---
{first_page_text}
--- END FIRST PAGE TEXT ---
"""
    print("🧠 Calling Groq LLM to extract title and author...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error calling Groq LLM for title/author: {e}")
        return json.dumps({"error": f"Error: {e}"})

def call_llm_for_abstract_summary_and_keywords(abstract_text):
    """
    Calls a Large Language Model (LLM) to extract a concise summary and
    relevant keywords from the provided abstract text.

    Args:
        abstract_text (str): The text content of the abstract.

    Returns:
        str: A JSON string containing the summary and keywords,
             or an error message if the LLM call fails.
    """
    prompt = f"""
You are an intelligent assistant skilled at summarizing scientific abstracts and extracting key terms.

Your task is to read the provided abstract text and return:
1.  A concise summary of the abstract (around 3-5 sentences).
2.  A list of relevant keywords (5-10 keywords) that best describe the content of the abstract.

Return the extracted information as a JSON object with the following fields:
- `abstract_summary`: A string containing the concise summary.
- `keywords`: An array of strings, where each string is a keyword.

Please only output the JSON object. Do not include any other text, comments, or explanations.

Example of desired JSON output format:

```json
{{
  "abstract_summary": "This is a concise summary of the abstract, outlining the main problem, method, results, and conclusions.",
  "keywords": ["star clusters", "photometry", "stochasticity", "galaxy evolution", "modeling"]
}}
```

-- BEGIN ABSTRACT TEXT ---
{abstract_text}
--- END ABSTRACT TEXT ---
"""
    print("🧠 Calling Groq LLM to summarize abstract and extract keywords...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error calling Groq LLM for abstract/keywords: {e}")
        return json.dumps({"error": f"Error: {e}"})

def call_llm_for_structured_chunks(text):
    """
    Calls a Large Language Model (LLM) to extract a structured Table of Contents (TOC)
    from the provided text.

    The prompt instructs the LLM to identify sections, subsections, and their
    corresponding start and end page numbers, returning the information as a JSON array.

    Args:
        text (str): The text content from the initial pages of a document,
                    expected to contain the Table of Contents.

    Returns:
        str: A JSON string representing the structured Table of Contents,
             or an error message if the LLM call fails.
    """
    # IMPORTANT: Double curly braces {{ and }} are used to escape literal curly braces
    # within the f-string, preventing them from being interpreted as format specifiers.
    prompt = f"""
You are an intelligent assistant skilled at extracting structured Table of Contents (TOC) from scientific documents, particularly PhD theses.

Your task is to identify all logical sections and subsections from the provided text, along with their precise start and end page numbers. The text provided will be the initial pages of a PhD thesis, where the Table of Contents is typically located.

**CRITICAL INSTRUCTIONS FOR TOC EXTRACTION:**
1.  **IDENTIFY THE MAIN TOC BLOCK**: First, identify the contiguous block of text that constitutes the **main, hierarchical Table of Contents** of the document. This block typically starts with an "INTRODUCTION" or a "1. [Chapter Title]" and contains numbered or clearly structured sections and subsections.
2.  **VERBATIM EXTRACTION ONLY**: You MUST extract entries that are **CLEARLY AND EXPLICITLY** part of this identified main TOC block as presented in the text.
3.  **NO INFERENCE/HALLUCINATION**: Each JSON object in the output array MUST correspond to a single, distinct entry verbatim from the TOC. Do NOT merge, summarize, infer, or create ANY titles or page numbers that are not directly visible in the provided TOC text. This is a paramount instruction.
4.  **EXCLUDE PRELIMINARY/NON-TOC CONTENT**: Explicitly **DO NOT** extract any titles, lists, or information that appears *before* or *outside* the identified main TOC block. This includes, but is not limited to:
    * Headings for preliminary sections (e.g., "LIST OF ORIGINAL PAPERS", "AUTHOR‘S CONTRUBUTION TO ORIGINAL PAPERS", the *heading* "TABLE OF CONTENTS" itself if it's just a title for the TOC and not an entry *within* the TOC, "Published contributions to academic conferences", "LIST OF FIGURES", "LIST OF TABLES").
    * Any other content that is clearly metadata or pre-content material, not part of the sequential, hierarchical list of chapters/sections with their corresponding page numbers.
5.  **PRECISE PAGE NUMBERS**: The `start_page` and `end_page` must be the **EXACT** page numbers explicitly listed in the TOC for that specific entry. Double-check this for accuracy. If a section is the last one in the document, its `end_page` should be "DOCUMENT_END".

Return the extracted TOC as a JSON array of objects. Each object in the array should represent a section or subsection and contain the following fields:
- `section_number`: The exact numerical section identifier (e.g., "1", "1.1", "2.3.1"). This field MUST ONLY contain Arabic numerals. If a section has an explicit Arabic numeral visible in the TOC, this field MUST contain that number. If a section does NOT have an explicit Arabic numeral (e.g., "REFERENCES", "INTRODUCTION", "Abstract", "LIST OF ABBREVIATIONS"), this field MUST be an empty string "". It should NEVER contain text that is part of the section title or non-Arabic numeral page identifiers.
- `section_title`: The **exact** title of the section or subsection **as it appears in the TOC**, **excluding** any Arabic numeral section number that is already captured in `section_number`. This field MUST contain only the title of that *specific* TOC entry. If a non-Arabic numeral prefix (like a Roman numeral or a letter used as a page identifier) is associated with the title in the TOC, it should remain part of the `section_title` if it's not an Arabic `section_number`.
- `level`: An integer representing the hierarchical level (e.g., 1 for "Chapter 1", 2 for "1.1.", 3 for "1.1.1.").

For sections with a `level` greater than 1, also include the following fields to indicate their parent sections:
- `parent_level_1_section_number`: The section number of the direct level 1 parent. Empty string if not applicable (i.e., if current level is 1).
- `parent_level_1_section_title`: The section title of the direct level 1 parent. Empty string if not applicable.

For sections with a `level` greater than 2, also include the following fields to indicate their grandparent sections:
- `parent_level_2_section_number`: The section number of the direct level 2 parent (grandparent). Empty string if not applicable (i.e., if current level is 1 or 2).
- `parent_level_2_section_title`: The section title of the direct level 2 parent (grandparent). Empty string if not applicable.

    (Add more `parent_level_X_...` fields as needed for deeper nesting, ensuring `parent_level_X` only appears if current `level` is greater than `X`).

For the `start_page` and `end_page` fields:
- `start_page`: The page number where this section officially begins, as indicated in the TOC. This MUST be the page number explicitly listed in the TOC for that specific entry.
- `end_page`: The page number where this section officially ends. This should be the `start_page` of the *next logical section* listed in the TOC, regardless of its level. If it's the very last section listed, its `end_page` should be "DOCUMENT_END".

Please only output the JSON array. Do not include any other text, comments, or explanations.

Example of desired JSON output format (This is a generic example to show the structure, not specific content from your PDF):

```json
[
  {{
    "section_number": "",
    "section_title": "Abstract",
    "level": 1,
    "start_page": 1,
    "end_page": 4
  }},
  {{
    "section_number": "1",
    "section_title": "Introduction to the Topic",
    "level": 1,
    "start_page": 5,
    "end_page": 10
  }},
  {{
    "section_number": "1.1",
    "section_title": "Background and Context",
    "level": 2,
    "parent_level_1_section_number": "1",
    "parent_level_1_section_title": "Introduction to the Topic",
    "start_page": 6,
    "end_page": 7
  }},
  {{
    "section_number": "1.1.1",
    "section_title": "Literature Review",
    "level": 3,
    "parent_level_1_section_number": "1",
    "parent_level_1_section_title": "Introduction to the Topic",
    "parent_level_2_section_number": "1.1",
    "parent_level_2_section_title": "Background and Context",
    "start_page": 8,
    "end_page": 10
  }},
  {{
    "section_number": "2",
    "section_title": "Methodology",
    "level": 1,
    "start_page": 15,
    "end_page": 20
  }},
  {{
    "section_number": "2.1",
    "section_title": "Experimental Setup",
    "level": 2,
    "parent_level_1_section_number": "2",
    "parent_level_1_section_title": "Methodology",
    "start_page": 16,
    "end_page": 20
  }},
  {{
    "section_number": "",
    "section_title": "Conclusion",
    "level": 1,
    "start_page": 30,
    "end_page": 31
  }},
  {{
    "section_number": "",
    "section_title": "References",
    "level": 1,
    "start_page": 32,
    "end_page": "DOCUMENT_END"
  }}
]
```

-- BEGIN PAPER TEXT ---
{text}
--- END PAPER TEXT ---
"""
    print("🧠 Calling Groq LLM to segment and annotate...")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            # Optionally, add response_format={"type": "json_object"} if your model supports it
            # and you want to enforce JSON output more strictly.
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error calling Groq LLM: {e}")
        return f"Error: {e}"

# calculate_end_pages function is REMOVED as per user's explicit request.

def get_section_text_from_pdf(pdf_path, start_page_1_indexed, end_page_1_indexed, total_doc_pages):
    """
    NEW FUNCTION: Extracts text from a given PDF file within a specified 1-indexed page range.
    This function is designed to read the content of individual sections based on
    the start_page and end_page provided by the LLM.

    Args:
        pdf_path (str): The file path to the PDF document.
        start_page_1_indexed (int): The 1-indexed starting page number for text extraction.
        end_page_1_indexed (int or str): The 1-indexed ending page number or "DOCUMENT_END".
        total_doc_pages (int): The total number of pages in the document. Required for "DOCUMENT_END".

    Returns:
        str: The concatenated text content from the specified page range.
    """
    extracted_text = ""
    try:
        with pymupdf.open(pdf_path) as doc:
            # Adjust to 0-indexed for PyMuPDF
            start_idx = start_page_1_indexed - 1
            
            if end_page_1_indexed == "DOCUMENT_END":
                end_idx = total_doc_pages - 1
            else:
                end_idx = end_page_1_indexed - 1

            # Ensure valid range
            start_idx = max(0, start_idx)
            end_idx = min(total_doc_pages - 1, end_idx)

            if start_idx > end_idx:
                print(f"⚠️ Invalid page range for text extraction: start={start_page_1_indexed}, end={end_page_1_indexed}. Returning empty string.")
                return "" # Return empty string if range is invalid (e.g., start > end)

            for i in range(start_idx, end_idx + 1):
                page = doc.load_page(i)
                extracted_text += page.get_text()
    except Exception as e:
        print(f"❌ Error extracting text from PDF pages {start_page_1_indexed}-{end_page_1_indexed}: {e}")
        return ""
    return extracted_text

def add_text_to_toc_entries(toc_list, pdf_path, total_doc_pages):
    """
    Reads the text content for each section in the provided TOC list
    and adds it to the corresponding JSON object with a keyword "text".
    """
    print("📝 Retrieving full text for each section...")
    for section in toc_list:
        start_p = section.get('start_page') # Retrieve start_page from the section dictionary
        end_p = section.get('end_page')   # Retrieve end_page from the section dictionary

        # Debugging print: Show the section being processed and its page range
        print(f"  Processing section: '{section.get('section_title', 'N/A')}', Start: {start_p}, End: {end_p}")

        section_text = "" # NEW: Initialize section_text to an empty string for safety

        # Proceed with text extraction only if both start_p and end_p are available
        if start_p is not None and end_p is not None:
            try:
                # Use the utility function to extract text for the specific page range
                section_text = get_section_text_from_pdf(pdf_path, start_page_1_indexed=start_p,
                                                        end_page_1_indexed=end_p,
                                                        total_doc_pages=total_doc_pages)
            except Exception as e:
                # NEW: Log any errors during text extraction but don't stop the process
                print(f"  ❌ Error during text extraction for section '{section.get('section_title', 'N/A')}': {e}")
        else:
            # NEW: Log if page numbers are missing for a section
            print(f"  ⚠️ Skipping text extraction for section due to missing page numbers: {section.get('section_title', 'N/A')}")
        
        section['text'] = section_text # Assign the extracted text (or empty string) to the 'text' key
        print(f"  Text added (first 100 chars): '{section['text'][:100]}...'") # Debugging print

    print("✅ All section texts retrieved and added.")
    return toc_list

# ---------- Run Pipeline ----------
if __name__ == "__main__":
    # Ensure the PDF file exists before proceeding
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: PDF file not found at {PDF_PATH}")
    else:
        print(f"📄 Extracting text from: {PDF_PATH} (first page for title/author, first 15 pages for TOC)")
        # Call extract_pdf_text to get first page text and TOC-relevant text
        first_page_text, raw_toc_text = extract_pdf_text(PDF_PATH, max_pages_toc=15)

        # NEW: Get total pages for full text extraction, explicitly outside any prior functions
        total_pdf_pages = 0
        try:
            with pymupdf.open(PDF_PATH) as doc:
                total_pdf_pages = doc.page_count
        except Exception as e:
            print(f"❌ Error getting total page count from {PDF_PATH}: {e}")
            # Do not exit, but set to a safe value to prevent errors later.
            # This might cause "DOCUMENT_END" to resolve incorrectly.
            total_pdf_pages = 1000000 # A very large number to simulate "DOCUMENT_END" working if count fails
                                    # Or, handle more gracefully, e.g., by skipping text extraction
                                    # if total_pdf_pages remains 0.
        # Ensure total_pdf_pages is at least 1 if document exists
        if total_pdf_pages == 0 and os.path.exists(PDF_PATH):
             print("⚠️  Warning: Total page count could not be determined, setting to 1.")
             total_pdf_pages = 1


        # Initialize parsed_title_author to ensure it's always a dictionary
        parsed_title_author = {}

        # Extract Title and Author
        if first_page_text:
            title_author_output = call_llm_for_title_and_author(first_page_text)
            try:
                parsed_title_author = json.loads(title_author_output)
                print("\n--- Document Title and Author ---")
                print(f"Title: {parsed_title_author.get('document_title', 'N/A')}")
                print(f"Author: {parsed_title_author.get('author', 'N/A')}")
                print("---------------------------------")
            except json.JSONDecodeError:
                print("\n--- Error parsing Title/Author LLM output ---")
                print(title_author_output)
                print("------------------------------------------")
        else:
            print("⚠️ No text extracted from the first page. Cannot extract title/author.")

        # Extract Abstract Summary and Keywords
        if raw_toc_text:
            abstract_keywords_output = call_llm_for_abstract_summary_and_keywords(raw_toc_text)
            try:
                parsed_abstract_keywords = json.loads(abstract_keywords_output)
                parsed_title_author.update(parsed_abstract_keywords)
                print("\n--- Abstract Summary and Keywords ---")
                print(f"Summary: {parsed_abstract_keywords.get('abstract_summary', 'N/A')}")
                print(f"Keywords: {', '.join(parsed_abstract_keywords.get('keywords', []))}")
                print("---------------------------------")
            except json.JSONDecodeError:
                print("\n--- Error parsing Abstract/Keywords LLM output ---")
                print(abstract_keywords_output)
                print("------------------------------------------")
        else:
            print("⚠️ No raw text for abstract. Skipping abstract summary and keyword extraction.")


        # Extract Table of Contents
        final_toc_output = [] # Initialize outside the if block
        if raw_toc_text:
            print("🚀 Sending TOC text to Groq for processing...")
            llm_full_toc_json = call_llm_for_structured_chunks(raw_toc_text)

            # Write the raw extracted text (for TOC) to a file for debugging/review
            with open(RAW_TEXT_OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(raw_toc_text)
            print(f"📝 Raw extracted text (first 15 pages for TOC) written to: {RAW_TEXT_OUTPUT_FILE}")

            # Process the LLM output and add text
            try:
                # DEBUG: Print the raw LLM output for TOC before parsing
                print("\n--- Raw LLM TOC Output for Debugging ---")
                print(llm_full_toc_json)
                print("----------------------------------------")

                parsed_toc_entries = json.loads(llm_full_toc_json)

                # DEBUG: Print parsed TOC entries after json.loads
                print("\n--- Parsed TOC Entries (after json.loads) for Debugging ---")
                print(json.dumps(parsed_toc_entries, indent=2))
                print("----------------------------------------------------------")

                # NEW: Call the new function to add section text (using LLM-provided start/end pages)
                # No programmatic calculate_end_pages here, as LLM is expected to provide end_page directly
                final_toc_output = add_text_to_toc_entries(parsed_toc_entries, PDF_PATH, total_pdf_pages)

                # Convert the final list of dictionaries back to a pretty-printed JSON string
                markdown_output = json.dumps(final_toc_output, indent=2)

                # Write the final structured TOC output (with text) to a file
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    f.write(markdown_output)
                print(f"✅ Final structured TOC output (with text) written to: {OUTPUT_FILE}")

                print("\n--- Final Parsed TOC Output (Pretty Printed) ---")
                print(markdown_output)
                print("------------------------------------------")

            except json.JSONDecodeError as e: # Catch the specific error for clarity
                print(f"\n--- ERROR: LLM TOC Output is NOT valid JSON! ---")
                print(f"Error details: {e}")
                print("Raw LLM output causing error:")
                print(llm_full_toc_json)
                print("------------------------------------------")
            except Exception as e:
                print(f"❌ An unexpected error occurred during TOC processing: {e}")
                print("\n--- Raw LLM Output (for debugging) ---")
                print(llm_full_toc_json)
                print("------------------------------------------")
        else:
            print("⚠️ No relevant text for TOC extracted from the PDF. Skipping TOC LLM call.")

        # Print the final combined metadata (title, author, abstract summary, keywords)
        if parsed_title_author:
            print("\n--- Final Combined Document Metadata ---")
            print(json.dumps(parsed_title_author, indent=2))
            print("------------------------------------------")
