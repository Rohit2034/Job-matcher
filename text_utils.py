from pypdf import PdfReader
from docx import Document

def extract_text(file_path: str) -> str:
    """Extract text from PDF, DOCX, or TXT files."""

    if file_path.lower().endswith(".pdf"):
        try:
            reader = PdfReader(file_path, strict=False)
            text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
            return text
        except Exception as e:
            print(f" Failed to extract PDF text from {file_path}: {e}")
            return ""

    if file_path.lower().endswith(".docx"):
        try:
            doc = Document(file_path)
            return " ".join(p.text for p in doc.paragraphs)
        except Exception as e:
            print(f" Failed to extract DOCX text from {file_path}: {e}")
            return ""

    if file_path.lower().endswith(".txt"):
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f" Failed to read TXT file {file_path}: {e}")
            return ""

    return ""
