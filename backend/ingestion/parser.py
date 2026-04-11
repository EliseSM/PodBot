import io


def parse_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def parse_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def parse_uploaded_file(filename: str, file_bytes: bytes) -> str:
    """
    Dispatches to the correct parser based on file extension.

    Supported extensions: .pdf, .docx, .txt
    Raises ValueError for unsupported types.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    dispatchers = {
        "pdf": parse_pdf,
        "docx": parse_docx,
        "txt": parse_txt,
    }
    if ext not in dispatchers:
        raise ValueError(f"Unsupported file type: .{ext}. Supported: pdf, docx, txt")
    return dispatchers[ext](file_bytes)
