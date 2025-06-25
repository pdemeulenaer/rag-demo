import pymupdf
import re

def get_document_title(doc):
    """
    Attempts to extract the document title using metadata and then heuristics.
    """
    # 1. Try to get title from metadata first
    metadata_title = doc.metadata.get("title")
    if metadata_title and metadata_title.strip() != "":
        print(f"Title (from metadata): '{metadata_title}'")
        return metadata_title

    print("Metadata title is empty or not found. Attempting heuristic extraction...")

    # 2. Heuristic extraction from the first few pages
    # Focus on the first page, but check next just in case
    pages_to_check = min(doc.page_count, 2) # Check first 2 pages

    potential_titles = []
    for page_num in range(pages_to_check):
        page = doc.load_page(page_num)
        
        # Get text blocks with detailed information (font, size, bbox)
        # Using 'dict' output provides more structured data.
        blocks = page.get_text("dict")["blocks"]
        
        current_page_largest_size = 0
        current_page_potential_title = ""

        for block in blocks:
            if block['type'] == 0:  # This is a text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        font_size = span["size"]
                        # Check if text is mostly uppercase (common for titles)
                        is_likely_title_case = text.isupper() or all(word[0].isupper() for word in text.split())

                        # Heuristic: largest font size on the page, and not too long
                        if font_size > current_page_largest_size and len(text.split()) < 25: # Arbitrary length limit
                            current_page_largest_size = font_size
                            current_page_potential_title = text
                        
                        # Add a condition for very large text even if not the absolute largest (e.g., if there's a huge logo)
                        # Also check if it's broadly centered (simple check based on bbox)
                        # More sophisticated centering would involve comparing x0 to page width
                        if font_size > 18 and len(text.split()) < 25: # Arbitrary size threshold
                            # Simple centering check: is the block's x0 not too far from page edge and x1 not too far from other edge?
                            # This is very rough and could be improved.
                            if block['bbox'][0] > page.rect.width * 0.1 and block['bbox'][2] < page.rect.width * 0.9:
                                potential_titles.append((font_size, text))

        if current_page_potential_title:
            potential_titles.append((current_page_largest_size, current_page_potential_title))

    # Sort potential titles by font size (descending) and prefer those on earlier pages
    potential_titles = sorted(list(set(potential_titles)), key=lambda x: x[0], reverse=True)

    if potential_titles:
        # Take the largest one that seems reasonable
        for size, text in potential_titles:
            # Filter out lines that are too short (e.g., "by", "Author Name")
            if len(text.split()) > 3: # A title is usually more than 3 words
                 print(f"Potential Title (heuristic): '{text}' (size: {size})")
                 return text
    
    return "Title Not Found (Heuristic)"



# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/Thesis_de_Meulenaer.pdf"
# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
PDF_PATH = "/home/philippe/Documents/vu_disertacijos/VU_disertacija_V. Liustrovaite.pdf"


OUTPUT_FILE = "structured_output.md"


doc = pymupdf.open(PDF_PATH)

metadata = doc.metadata
print(metadata)
title = metadata.get("title", "Title Not Found")
print("Title (from metadata):", title)


toc = doc.get_toc()
for level, title, page_num, *_ in toc:
    print(f"Level {level}: {title} (Page {page_num})")

document_title = get_document_title(doc)
print("Final Document Title:", document_title)

print()

# --- Section Extraction ---
sections = []
toc = doc.get_toc()

if not toc:
    print("No Table of Contents found. Cannot extract sections based on ToC.")
    # You would need to implement regex/heuristic section detection here if no ToC
else:
    # Prepare section boundaries from ToC
    for i, (level, title, page_num, *_) in enumerate(toc):
        # PyMuPDF page numbers are 1-based, convert to 0-based index
        start_page_idx = page_num - 1 
        
        # Determine the end page for the current section
        end_page_idx = doc.page_count - 1 # Default to end of document
        if i + 1 < len(toc):
            next_section_page_num = toc[i+1][2]
            end_page_idx = next_section_page_num - 2 # Go one page BEFORE the next section starts

        # If a section ends on the same page as the next starts (e.g., small sections),
        # ensure end_page_idx is not less than start_page_idx
        if end_page_idx < start_page_idx:
            end_page_idx = start_page_idx # Section is only on this one page

        sections.append({
            "level": level,
            "title": title,
            "start_page": start_page_idx, # 0-based
            "end_page": end_page_idx      # 0-based
        })

    # Now, extract text for each section
    structured_content = []

    for section in sections:
        section_text = []
        for page_idx in range(section["start_page"], section["end_page"] + 1):
            if 0 <= page_idx < doc.page_count: # Ensure page index is valid
                page = doc.load_page(page_idx)
                text = page.get_text("text") # Simple text extraction
                section_text.append(text)
        
        # Clean up concatenated text (remove multiple newlines, leading/trailing whitespace)
        full_section_text = "\n".join(section_text)
        full_section_text = re.sub(r'\n\s*\n', '\n\n', full_section_text).strip() # Reduce excessive newlines
        
        structured_content.append({
            "level": section["level"],
            "title": section["title"],
            "text": full_section_text
        })

    # Optional: Print/Save the structured content
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Document Title: {document_title}\n\n")
        f.write(f"## Metadata:\n")
        for key, value in doc.metadata.items():
            f.write(f"- {key}: {value}\n")
        f.write("\n")

        for entry in structured_content:
            # Use Markdown headings based on section level
            heading_prefix = "#" * min(entry["level"] + 1, 6) # Max H6
            f.write(f"{heading_prefix} {entry['title']}\n\n")
            f.write(entry['text'])
            f.write("\n\n---\n\n") # Separator between sections

    print(f"\nExtracted {len(structured_content)} sections and saved to {OUTPUT_FILE}")


doc.close()    


# def parse_thesis(pdf_path):
#     doc = pymupdf.open(pdf_path)

#     # 1. Get Metadata
#     metadata = doc.metadata
#     print("Metadata:", metadata)

#     # 2. Try to get title from metadata first
#     title = metadata.get("title", "Title Not Found")
#     print("Title (from metadata):", title)

#     # 3. Process first few pages for more details (title, abstract, sections)
#     full_text = ""
#     for page_num in range(min(doc.page_count, 5)): # Process first 5 pages
#         page = doc.load_page(page_num)
#         blocks = page.get_text("dict")["blocks"]

#         for block in blocks:
#             if block['type'] == 0: # text block
#                 for line in block["lines"]:
#                     for span in line["spans"]:
#                         text = span["text"].strip()
#                         font_size = span["size"]
#                         # Heuristic for Title: Largest font on first page
#                         if page_num == 0 and font_size > 20 and len(text.split()) < 15: # Arbitrary size/length
#                             if "Title Not Found" in title: # Only if not found in metadata
#                                 title = text
#                                 print(f"Potential Title (from text): {title} (size: {font_size})")

#                         # Heuristic for Abstract: Look for "Abstract" heading
#                         if "abstract" in text.lower() and font_size > 12: # Likely a heading
#                             # This is tricky: need to capture subsequent paragraphs
#                             print(f"Potential Abstract heading: {text} (size: {font_size})")
#                         full_text += text + "\n"

#     # This part needs more advanced logic for real sectioning
#     # You'd typically look for patterns like "1. Introduction", "CHAPTER I", or consistent bold/large text
#     # A simple regex for section numbers:
    
#     sections = re.findall(r"(\n[0-9]+\.?\s+[A-Z][a-zA-Z\s]+|\n[A-Z][a-zA-Z\s]+)", full_text[:5000]) # Look in first 5000 chars for initial sections
#     print("Potential Sections (basic regex):", sections)

#     doc.close()
#     return {"metadata": metadata, "title": title, "abstract": "Needs more robust extraction", "sections_found": sections}

# thesis_info = parse_thesis(PDF_PATH)