"""
BrandMind — PDF Knowledge Extraction Module
Extracts text, metadata, and structural sections from raw brand PDFs with strict page traceability.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pypdf import PdfReader


class ExtractedPage:
    def __init__(self, brand_id: str, source_file: str, page_number: int, text: str):
        self.brand_id = brand_id
        self.source_file = source_file
        self.page_number = page_number
        self.text = text.strip()

    def to_dict(self) -> Dict[str, any]:
        return {
            "brand_id": self.brand_id,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "char_count": len(self.text),
            "text": self.text,
        }


class PDFExtractor:
    """Extracts text and page-level metadata from PDF files in data/raw/<brand>/."""

    def __init__(self, brand_id: str, raw_dir: Optional[str] = None):
        self.brand_id = brand_id
        self.raw_dir = Path(raw_dir) if raw_dir else Path("data/raw") / brand_id

    def extract_document(self, filename: str) -> List[ExtractedPage]:
        pdf_path = self.raw_dir / filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF document not found: {pdf_path}")

        reader = PdfReader(str(pdf_path))
        pages: List[ExtractedPage] = []

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages.append(
                ExtractedPage(
                    brand_id=self.brand_id,
                    source_file=filename,
                    page_number=idx + 1,
                    text=page_text,
                )
            )

        return pages

    def extract_all(self) -> Dict[str, List[ExtractedPage]]:
        """Extracts all PDF documents found in the brand raw directory."""
        if not self.raw_dir.exists():
            raise FileNotFoundError(f"Raw directory does not exist: {self.raw_dir}")

        results: Dict[str, List[ExtractedPage]] = {}
        for pdf_file in self.raw_dir.glob("*.pdf"):
            results[pdf_file.name] = self.extract_document(pdf_file.name)

        return results


if __name__ == "__main__":
    extractor = PDFExtractor(brand_id="rlvnt")
    extracted = extractor.extract_all()
    for fname, pages in extracted.items():
        print(f"Extracted {fname}: {len(pages)} pages.")
