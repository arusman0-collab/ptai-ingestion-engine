from pathlib import Path
def extract_pdf(path: Path) -> tuple[str,dict]:
    import fitz
    doc=fitz.open(path); pages=[page.get_text("text") for page in doc]
    text="\n\n".join(f"[Page {i+1}]\n{p.strip()}" for i,p in enumerate(pages) if p.strip())
    if not text.strip(): raise ValueError("PDF has no embedded text; OCR is intentionally not performed in Phase 1")
    return text, {"method":"pdf_embedded_text","page_count":len(doc),"library":"PyMuPDF"}