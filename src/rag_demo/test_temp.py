import pymupdf
import re

# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/Thesis_de_Meulenaer.pdf"
# PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"
PDF_PATH = "/home/philippe/Documents/vu_disertacijos/IG_Disertacija be straipsniu.pdf"
# PDF_PATH = "/home/philippe/Documents/vu_disertacijos/VU_disertacija_V. Liustrovaite.pdf"
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


def _longest_common_prefix(strs):
    if not strs:
        return ""
    shortest = min(strs, key=len)
    for i, char in enumerate(shortest):
        for other in strs:
            if other[i] != char:
                return shortest[:i]
    return shortest


def _synthesize_title(sections, prefix):
    candidates = []
    prefix_level = len(prefix.split('.'))

    def search(subsections):
        for s in subsections:
            match = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)", s["title"])
            if match:
                section_number = match.group(1)
                section_parts = section_number.split('.')
                
                # Check if this section's number is exactly one level deeper than the prefix
                if section_number.startswith(prefix + '.') and len(section_parts) == prefix_level + 1:
                    candidates.append(s["title"])
                
                # Recursively search children if the current section is an ancestor or matches the prefix itself
                if section_number.startswith(prefix) and s.get("children"):
                    search(s["children"])

    search(sections) # Start search from the root of the TOC

    if not candidates:
        return prefix

    titles_without_numbers = []
    for title in candidates:
        match = re.match(r"^(\d+(?:\.\d+)*)\s*(.*)", title)
        if match:
            titles_without_numbers.append(match.group(2).strip())
        else:
            titles_without_numbers.append(title.strip())

    if not titles_without_numbers:
        return prefix

    lcp = _longest_common_prefix(titles_without_numbers).strip()
    return f"{prefix} {lcp}" if lcp else prefix


def flatten_sections(sections, parent_hierarchy=None):
    if parent_hierarchy is None:
        parent_hierarchy = []

    flat = []

    for section in sections:
        current_title = section["title"]
        
        # Start with the hierarchy from the parent
        current_full_hierarchy = list(parent_hierarchy) 

        match = re.match(r"^(\d+(?:\.\d+)+)\s+.*", current_title)
        if match:
            parts = match.group(1).split(".")
            
            # Iterate through numerical parts of the current title to build intermediate hierarchy
            # Example: for 1.2.2, check 1. and 1.2.
            for i in range(1, len(parts)): # Iterate up to the parent's numerical part
                ancestor_number = ".".join(parts[:i])
                
                # Check if this ancestor (by numerical prefix) is already in our current_full_hierarchy
                # We need to ensure we don't duplicate existing entries or miss new ones
                found_in_current_hierarchy = False
                for h_title in current_full_hierarchy:
                    h_match = re.match(r"^(\d+(?:\.\d+)*)\s*(.*)", h_title)
                    if (h_match and h_match.group(1) == ancestor_number) or h_title == ancestor_number:
                        found_in_current_hierarchy = True
                        break
                
                if not found_in_current_hierarchy:
                    # If not found, infer and add it
                    inferred_title = _synthesize_title(sections, ancestor_number)
                    if inferred_title:
                        current_full_hierarchy.append(inferred_title)
                    else:
                        current_full_hierarchy.append(ancestor_number) # Fallback if no inference
            
        # Finally, add the current section's title
        current_full_hierarchy.append(current_title)

        flat.append({
            "hierarchy": current_full_hierarchy,
            "start_page": section["start_page"],
            "end_page": section["end_page"]
        })

        if section["children"]:
            # Pass the constructed current_full_hierarchy for children to build upon
            flat.extend(flatten_sections(section["children"], current_full_hierarchy))

    return flat


def extract_text_by_page_range(doc, start_page, end_page, section_title=None, next_section_title=None):
    import re
    import fitz

    text_blocks = []
    started = False
    section_pattern = re.escape(section_title.strip()) if section_title else None
    next_section_pattern = re.escape(next_section_title.strip()) if next_section_title else None

    def remove_page_numbers(lines):
        cleaned_lines = []
        for line in lines:
            if re.fullmatch(r"^\s*\d+\s*$", line.strip()):
                continue
            cleaned_lines.append(line)
        return cleaned_lines

    for page_idx in range(start_page - 1, end_page):
        if 0 <= page_idx < doc.page_count:
            page = doc.load_page(page_idx)
            text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES)
            lines = text.splitlines()

            lines = remove_page_numbers(lines)

            clean_lines = []
            include_lines = True

            for line in lines:
                if started and next_section_pattern and re.search(next_section_pattern, line, re.IGNORECASE):
                    include_lines = False
                    continue

                if not started and section_pattern and re.search(r'\b' + section_pattern + r'\b', line, re.IGNORECASE):
                    started = True
                    continue

                if started and include_lines:
                    clean_lines.append(line)

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
                continue

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
