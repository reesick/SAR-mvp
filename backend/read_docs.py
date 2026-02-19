import docx
import sys
import os

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"

files = [
    r"d:\barclays\1.0.docx",
    r"d:\barclays\GPT1.0.docx"
]


print("--- START EXTRACT ---")
with open("requirements_dump.txt", "w", encoding="utf-8") as out:
    for f in files:
        out.write(f"\n=== FILE: {os.path.basename(f)} ===\n")
        if os.path.exists(f):
            content = read_docx(f)
            out.write(content)
            out.write("\n\n")
        else:
            out.write(f"File not found: {f}\n")
print("--- EXTRACTION COMPLETE ---")
