---
name: pdf-knowledge-extraction
description: Authoritative extraction of text, visual lookbooks, tables, and brand metadata from fashion/streetwear PDFs with strict source-to-fact mapping.
---

# PDF Knowledge Extraction Skill

## Purpose
This skill governs the extraction, normalization, and auditing of raw PDF documents (governance manuals, product catalogs, visual lookbooks) into verified, traceable knowledge chunks and structured database tables.

## When to Activate
- Ingesting new brand documents or product lookbooks from `data/raw/<brand>/`.
- Parsing tables, product descriptions, care labels, or policy clauses.
- Resolving inconsistencies or updating the source-of-truth matrix in `docs/RLVNT_SOURCE_AUDIT.md`.

## Technical Instructions
1. **Extraction Pipeline:**
   - Use `pypdf` or `pymupdf` (`fitz`) for native digital text extraction.
   - For visual lookbooks containing graphic text or slide imagery, run OCR inspection or extract high-fidelity visual descriptions.
   - Always preserve document metadata: `source_file`, `source_page`, `document_type`, and `brand_id`.
2. **Data Separation:**
   - Split unstructured prose (brand pillars, policies, garment care) for vector ingestion.
   - Convert catalog slides and structured parameters (SKUs, categories, prices, return windows) into tabular CSV format (`products.csv`, `policies.csv`).
3. **Traceability Rule:**
   - Every extracted factual clause must maintain a direct citation to its source file and page number.
   - Never invent or impute missing operational values; record them explicitly as `UNKNOWN` or document them as template placeholders.

## Testing & Validation Checklist
- [ ] Document page count matches extracted chunk count.
- [ ] No empty or whitespace-only chunks.
- [ ] Numeric values in structured tables strictly match the source PDF prose.
- [ ] `docs/RLVNT_SOURCE_AUDIT.md` updated with all verified facts.
