import pymupdf
import re

# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/Thesis_de_Meulenaer.pdf"
# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
PDF_PATH = "/home/philippe/Documents/vu_disertacijos/VU_disertacija_V. Liustrovaite.pdf"
OUTPUT_FILE = "structured_output.md"


def extract_sections_with_hierarchy(doc):
    toc = doc.get_toc()
    if not toc:
        raise ValueError("No Table of Contents found in the PDF.")

    stack = []
    sections = []

    for i, (level, title, page_num, *_) in enumerate(toc):
        if not title or not isinstance(page_num, int) or page_num < 1:
            continue

        title = title.strip()
        section = {
            "level": level,
            "title": title,
            "start_page": page_num,
            "end_page": doc.page_count,
            "children": [],
        }

        for j in range(i + 1, len(toc)):
            next_level, _, next_page, *_ = toc[j]
            if next_page > page_num:
                section["end_page"] = next_page
                break

        while stack and stack[-1]["level"] >= level:
            stack.pop()

        if stack:
            stack[-1]["children"].append(section)
        else:
            sections.append(section)

        stack.append(section)

    return sections




def _synthesize_title(sections, prefix):
    import re
    candidates = []

    def search(subsections):
        for s in subsections:
            match = re.match(rf"^{re.escape(prefix)}(\.\d+)?\s+(.*)", s["title"])
            if match:
                candidates.append(s["title"])
            if s.get("children"):
                search(s["children"])

    search(sections)

    if not candidates:
        return prefix  # fallback to number only

    # Return longest matching prefix (assumes proper title structure)
    return _longest_common_prefix(candidates).strip()



def flatten_sections(sections, parent_hierarchy=None, seen=None):
    import re
    if parent_hierarchy is None:
        parent_hierarchy = []
    if seen is None:
        seen = set()

    flat = []

    for section in sections:
        title = section["title"]
        current_hierarchy = parent_hierarchy + [title]

        # Check if title has a numbered prefix like "1.2.1."
        match = re.match(r"^(\d+(?:\.\d+)+)\s+.*", title)
        if match:
            parts = match.group(1).split(".")
            for i in range(1, len(parts)):
                ancestor_number = ".".join(parts[:i])
                # Skip if already seen
                if ancestor_number in seen:
                    continue
                # Try to synthesize a title from child section titles
                inferred_title = _synthesize_title(sections, ancestor_number)
                if inferred_title:
                    injected_hierarchy = parent_hierarchy + [inferred_title]
                    flat.append({
                        "hierarchy": injected_hierarchy,
                        "start_page": section["start_page"],
                        "end_page": section["end_page"]
                    })
                    seen.add(ancestor_number)

        flat.append({
            "hierarchy": current_hierarchy,
            "start_page": section["start_page"],
            "end_page": section["end_page"]
        })

        if section["children"]:
            flat.extend(flatten_sections(section["children"], current_hierarchy, seen))

    return flat




# def extract_text_by_page_range(doc, start_page, end_page):
#     text = []
#     for i in range(start_page, end_page + 1):
#         page = doc.load_page(i)
#         page_text = page.get_text("text")
#         text.append(page_text)
#     return re.sub(r'\n\s*\n', '\n\n', "\n".join(text).strip())

# def extract_text_by_page_range(doc, start_page, end_page, section_title=None, next_section_title=None):
#     import re
#     import fitz  # PyMuPDF

#     text_blocks = []
#     started = False

#     section_pattern = re.escape(section_title.strip()) if section_title else None
#     next_section_pattern = re.escape(next_section_title.strip()) if next_section_title else None

#     for page_idx in range(start_page, end_page + 1):
#         if 0 <= page_idx < doc.page_count:
#             page = doc.load_page(page_idx)
#             text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES)
#             lines = text.splitlines()

#             # Remove page numbers
#             lines = [line for line in lines if not re.fullmatch(r"\s*\d{1,4}\s*", line.strip())]

#             clean_lines = []

#             for line in lines:
#                 if not started and section_pattern and re.search(section_pattern, line, re.IGNORECASE):
#                     started = True  # Start collecting lines after we hit the section title

#                 if started:
#                     if next_section_pattern and re.search(next_section_pattern, line, re.IGNORECASE):
#                         started = False
#                         break  # Stop collecting if we hit the next section title
#                     clean_lines.append(line)

#             if clean_lines:
#                 text_blocks.append("\n".join(clean_lines).strip())

#     return "\n".join(text_blocks).strip()


def extract_text_by_page_range(doc, start_page, end_page, section_title=None, next_section_title=None):
    import re
    import fitz  # PyMuPDF

    text_blocks = []
    started = False
    section_pattern = re.escape(section_title.strip()) if section_title else None
    next_section_pattern = re.escape(next_section_title.strip()) if next_section_title else None

    for page_idx in range(start_page - 1, end_page):  # Convert to 0-based for PyMuPDF
        if 0 <= page_idx < doc.page_count:
            page = doc.load_page(page_idx)
            text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES)
            lines = text.splitlines()

            # Remove page numbers
            lines = [line for line in lines if not re.fullmatch(r"\s*\d{1,4}\s*", line.strip())]

            clean_lines = []
            include_lines = True  # Flag to control whether to include lines

            for line in lines:
                # Stop collecting if we hit the next section title
                if started and next_section_pattern and re.search(next_section_pattern, line, re.IGNORECASE):
                    include_lines = False
                    continue  # Skip the next section title line itself

                # Start collecting after the section title
                if not started and section_pattern and re.search(section_pattern, line, re.IGNORECASE):
                    started = True
                    continue  # Skip the section title line itself

                # Collect lines if in the section and before next section title
                if started and include_lines:
                    clean_lines.append(line)

            # Append non-empty text blocks for the page
            if clean_lines:
                text_blocks.append("\n".join(clean_lines).strip())

    return "\n".join(text_blocks).strip()



def main():
    doc = pymupdf.open(PDF_PATH)
    structured_sections = extract_sections_with_hierarchy(doc)
    lowest_sections = flatten_sections(structured_sections)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for i, section in enumerate(lowest_sections):
            next_title = (
                lowest_sections[i + 1]["hierarchy"][-1]
                if i + 1 < len(lowest_sections)
                else None
            )

            chunk_text = extract_text_by_page_range(
                doc,
                section["start_page"],
                section["end_page"],
                section_title=section["hierarchy"][-1],
                next_section_title=next_title
            )

            if not chunk_text.strip():
                print(f"Skipping empty chunk: {section['hierarchy']}")
                continue  # Skip empty chunks

            metadata = {
                "section_hierarchy": section["hierarchy"],
                "start_page": section["start_page"],
                "end_page": section["end_page"]
            }

            f.write(f"## Chunk {i + 1}\n")
            f.write("**Metadata**:\n")
            f.write(f"- **Hierarchy**: {section['hierarchy']}\n")
            f.write(f"- **Start Page**: {section['start_page']}\n")
            f.write(f"- **End Page**: {section['end_page']}\n\n")
            f.write(f"{chunk_text}\n\n---\n\n")


    doc.close()
    print(f"Extracted {len(lowest_sections)} chunks to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()






# doc = pymupdf.open(PDF_PATH)

# metadata = doc.metadata
# print(metadata)
# title = metadata.get("title", "Title Not Found")
# print("Title (from metadata):", title)


# toc = doc.get_toc()
# for level, title, page_num, *_ in toc:
#     print(f"Level {level}: {title} (Page {page_num})")

# document_title = get_document_title(doc)
# print("Final Document Title:", document_title)

# print()

# # --- Section Extraction ---
# sections = []
# toc = doc.get_toc()

# if not toc:
#     print("No Table of Contents found. Cannot extract sections based on ToC.")
#     # You would need to implement regex/heuristic section detection here if no ToC
# else:
#     # Prepare section boundaries from ToC
#     for i, (level, title, page_num, *_) in enumerate(toc):
#         # PyMuPDF page numbers are 1-based, convert to 0-based index
#         start_page_idx = page_num - 1 
        
#         # Determine the end page for the current section
#         end_page_idx = doc.page_count - 1 # Default to end of document
#         if i + 1 < len(toc):
#             next_section_page_num = toc[i+1][2]
#             end_page_idx = next_section_page_num - 2 # Go one page BEFORE the next section starts

#         # If a section ends on the same page as the next starts (e.g., small sections),
#         # ensure end_page_idx is not less than start_page_idx
#         if end_page_idx < start_page_idx:
#             end_page_idx = start_page_idx # Section is only on this one page

#         sections.append({
#             "level": level,
#             "title": title,
#             "start_page": start_page_idx, # 0-based
#             "end_page": end_page_idx      # 0-based
#         })

#     # Now, extract text for each section
#     structured_content = []

#     for section in sections:
#         section_text = []
#         for page_idx in range(section["start_page"], section["end_page"] + 1):
#             if 0 <= page_idx < doc.page_count: # Ensure page index is valid
#                 page = doc.load_page(page_idx)
#                 text = page.get_text("text") # Simple text extraction
#                 section_text.append(text)
        
#         # Clean up concatenated text (remove multiple newlines, leading/trailing whitespace)
#         full_section_text = "\n".join(section_text)
#         full_section_text = re.sub(r'\n\s*\n', '\n\n', full_section_text).strip() # Reduce excessive newlines
        
#         structured_content.append({
#             "level": section["level"],
#             "title": section["title"],
#             "text": full_section_text
#         })

#     # Optional: Print/Save the structured content
#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         f.write(f"# Document Title: {document_title}\n\n")
#         f.write(f"## Metadata:\n")
#         for key, value in doc.metadata.items():
#             f.write(f"- {key}: {value}\n")
#         f.write("\n")

#         for entry in structured_content:
#             # Use Markdown headings based on section level
#             heading_prefix = "#" * min(entry["level"] + 1, 6) # Max H6
#             f.write(f"{heading_prefix} {entry['title']}\n\n")
#             f.write(entry['text'])
#             f.write("\n\n---\n\n") # Separator between sections

#     print(f"\nExtracted {len(structured_content)} sections and saved to {OUTPUT_FILE}")


# doc.close()    





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