# from docling.document_converter import DocumentConverter

# source = "https://arxiv.org/pdf/2408.09869"
# converter = DocumentConverter()
# doc = converter.convert(source).document
# print(doc.export_to_markdown())

import time
from pathlib import Path
from docling.document_converter import DocumentConverter
import os


# 1. Start timer for Initialization (Loading AI models into memory)
init_start = time.perf_counter()
converter = DocumentConverter()
init_end = time.perf_counter()

# 2. Start timer for Conversion (The actual processing)
# source = "https://arxiv.org/pdf/2408.09869"
source = "https://arxiv.org/pdf/1502.04839"
filename = os.path.basename(source).replace(".pdf", ".md")

conv_start = time.perf_counter()

# 2.1 Conversion
result = converter.convert(source)

# 2.2 Generate the markdown string
markdown_content = result.document.export_to_markdown()

# 2.3 Define the output file path
output_path = Path(filename)

# 2.4 Write the content to the file
with output_path.open("w", encoding="utf-8") as f:
    f.write(markdown_content)

conv_end = time.perf_counter()

# 3. Calculate metrics
init_time = init_end - init_start
conv_time = conv_end - conv_start
num_pages = len(result.document.pages) if hasattr(result.document, 'pages') else 1
sec_per_page = conv_time / num_pages

print(f"--- Docling Benchmark ---")
print(f"Model Initialization: {init_time:.2f} seconds")
print(f"Total Conversion Time: {conv_time:.2f} seconds")
print(f"Number of Pages: {num_pages}")
print(f"Average Speed: {sec_per_page:.2f} seconds per page")
print(f"-------------------------")

# Optional: Print the first 500 characters of Markdown
# print(result.document.export_to_markdown()[:500])