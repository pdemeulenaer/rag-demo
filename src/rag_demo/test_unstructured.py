from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title

# Load and chunk the PDF
elements = partition_pdf(
    filename="/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf",  # Replace with your file path
    strategy="hi_res",                # or "fast" for speed
    infer_table_structure=True
)

# Group content by section
chunks = []
current_section = {"title": None, "content": []}

for el in elements:
    if isinstance(el, Title):
        if current_section["title"] or current_section["content"]:
            chunks.append(current_section)
        current_section = {"title": el.text.strip(), "content": []}
    else:
        if el.text:
            current_section["content"].append(el.text.strip())

# Append final section
if current_section["title"] or current_section["content"]:
    chunks.append(current_section)

# Write chunks to file
with open("chunks_output.txt", "w", encoding="utf-8") as f:
    for i, chunk in enumerate(chunks, start=1):
        title = chunk["title"] or f"Untitled Section {i}"
        content = "\n".join(chunk["content"])
        f.write(f"=== Section {i}: {title} ===\n")
        f.write(content)
        f.write("\n\n")
