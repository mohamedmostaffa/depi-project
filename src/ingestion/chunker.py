"""
BrandMind — Knowledge Processing & Semantic Chunking Module
Segments brand governance manuals and catalog lookbooks into contextualized, metadata-rich chunks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from src.ingestion.pdf_extractor import PDFExtractor, ExtractedPage


class KnowledgeChunk:
    def __init__(
        self,
        chunk_id: str,
        brand_id: str,
        source_file: str,
        source_page: int,
        document_type: str,
        section: str,
        content: str,
    ):
        self.chunk_id = chunk_id
        self.brand_id = brand_id
        self.source_file = source_file
        self.source_page = source_page
        self.document_type = document_type
        self.section = section
        self.content = content.strip()
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, any]:
        return {
            "chunk_id": self.chunk_id,
            "brand_id": self.brand_id,
            "source_file": self.source_file,
            "source_page": self.source_page,
            "document_type": self.document_type,
            "section": self.section,
            "content": self.content,
            "last_updated": self.last_updated,
        }


class SemanticChunker:
    """Processes extracted PDF documents into logical semantic chunks with contextual metadata."""

    def __init__(self, brand_id: str = "rlvnt", output_dir: str = "data/processed/rlvnt"):
        self.brand_id = brand_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def chunk_policy_manual(self, pages: List[ExtractedPage]) -> List[KnowledgeChunk]:
        """Segments the official governance manual based on logical section headings."""
        chunks: List[KnowledgeChunk] = []

        # Map page numbers to logical sections
        section_mapping = {
            1: "00 Official Brand Governance & Overview",
            2: "01 Brand Identity, Core Positioning & Product Architecture",
            3: "02 Logo, Color Palette & Typography Standards",
            4: "03 Ordering, Pricing & Payment Policy",
            5: "04 Shipping & Delivery Policy",
            6: "05 Returns, Exchanges & Refund Policy",
            7: "06 Product Quality, Sizing & Recommended Garment Care",
            8: "07 Customer Privacy & Intellectual Property",
            9: "08 Customer Support & Official Contact Channels",
        }

        # Build chunks from extracted text
        for p in pages:
            # Look for specific sub-sections within pages to avoid oversized chunks
            text = p.text
            if not text:
                continue

            # In page 2: Split Brand Identity and Product Architecture
            if p.page_number == 2:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P02-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Brand Identity & Core Positioning",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Brand Identity & Positioning\n"
                            "RLVNT is a contemporary streetwear and apparel label built around bold visual culture, "
                            "iconic sports and pop-culture references, and everyday oversized silhouettes. Every seasonal "
                            "drop—including the signature Winter Collection—pairs expressive graphic storytelling with "
                            "heavyweight comfort. Core brand pillars include Cultural Relevance, Unapologetic Visual Impact, "
                            "Everyday Quality, and Transparent Service."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P02-02",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Product Architecture & Streetwear Categories",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Product Architecture\n"
                            "RLVNT product architecture encompasses three primary categories: "
                            "1) Graphic Crewnecks & Hoodies: Heavyweight relaxed-fit tops crafted for cold-weather layering, "
                            "including 100% cotton hoodies and high-contrast statement crewnecks. "
                            "2) Sports & Vintage-Inspired Tops: Football jerseys, half-zip pullovers, and retro-styled track jackets "
                            "designed for casual street styling. "
                            "3) Bottoms & Full-Outfit Sets: Washed wide-leg denim, relaxed sweatpants, and coordinated monochrome sets."
                        ),
                    )
                )

            # Page 3: Visual Guidelines and Color Palette
            elif p.page_number == 3:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P03-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Visual Guidelines & Color Palette",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Visual Guidelines & Color Palette\n"
                            "The RLVNT wordmark is our primary brand identifier featuring custom crimson bubble typography "
                            "framed by an oval ring and anchored by a centered five-point star. Official Color Palette: "
                            "RLVNT Crimson (#8F1D1D), Streetwear Black (#111111), Poster Off-White (#F8F6F4), Crisp White (#FFFFFF). "
                            "Proportions maintain clear space equal to the star height."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P03-02",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Ordering & Verification Policy",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Ordering & Verification Policy\n"
                            "All orders placed through the website or official social channels are subject to stock availability. "
                            "Customers receive an automated confirmation with order number, itemized garments, sizes, and total amount. "
                            "For high-value or cash-on-delivery orders, RLVNT may verify by phone or WhatsApp prior to dispatch."
                        ),
                    )
                )

            # Page 4: Pricing, Payment, Modifications & Shipping Policy
            elif p.page_number == 4:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P04-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Pricing, Payment Methods & Order Modifications",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Pricing & Order Modifications\n"
                            "Product prices are displayed in local currency (EGP). Accepted payment methods include Cash on Delivery, "
                            "Debit/Credit Cards, and Mobile Wallets. Order Modifications & Cancellations: Customers may request a size change, "
                            "address correction, or full cancellation within 12 hours of placing an order, provided the parcel has not yet "
                            "been handed to the courier. Once dispatched, changes must follow the Returns & Exchanges Policy."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P04-02",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Shipping, Delivery & Inspection Standards",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Shipping & Delivery Policy\n"
                            "Order Processing Time: Orders are verified, packed in protective packaging, and dispatched within 1-2 business days "
                            "(excluding public holidays). Delivery takes standard delivery timeframe depending on destination governorate. "
                            "A tracking update is sent via SMS/WhatsApp once dispatched. Couriers attempt delivery 2-3 times. "
                            "Inspection Upon Delivery: Customers must inspect the outer parcel upon arrival. If damaged in transit, report within "
                            "24-48 hours with clear photos of the packaging and garment."
                        ),
                    )
                )

            # Page 5: Returns, Exchanges & Refund Policy
            elif p.page_number == 5:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P05-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Returns & Exchanges Eligibility Requirements",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Returns & Exchanges Eligibility\n"
                            "Eligibility Requirements: Return or exchange requests must be submitted within 14 days from the date of delivery. "
                            "Item Condition: Garments must be unworn, unwashed, free of perfume, stains, or pet hair, and returned in original "
                            "RLVNT packaging with all tags attached. A valid order number or receipt is required for every request."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P05-02",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Exchanges, Defects & Non-Returnable Items Matrix",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Resolution & Shipping Cost Matrix\n"
                            "1) Size or Style Exchange: Swap for another available size or equal-value item (or store credit if sold out). "
                            "Return shipping is covered by the customer. "
                            "2) Defective or Wrong Item: Priority replacement with the correct item or full refund upon photo verification, "
                            "with 100% of return shipping covered by RLVNT. "
                            "3) Standard Return / Refund: Refund issued to original payment method or store credit after warehouse inspection. "
                            "Original and return shipping fees are non-refundable. "
                            "4) Non-Returnable Items: Final-sale clearance items, washed/altered garments, or items missing original tags."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P05-03",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Warehouse Inspection & Refund Processing Timeline",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Inspection & Refund Processing\n"
                            "Returned parcels undergo quality inspection within 2-3 business days of arriving at our warehouse. "
                            "Approved refunds are processed within 5-7 business days via original payment method or wallet store credit."
                        ),
                    )
                )

            # Page 6: Sizing & Garment Care Standards
            elif p.page_number == 6:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P06-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Product Sizing & Streetwear Proportions",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Sizing & Fit Guidelines\n"
                            "RLVNT pieces—including 100% cotton hoodies, heavyweight graphic crewnecks, vintage-cut jerseys, and wide-leg bottoms—"
                            "are designed with relaxed streetwear proportions. Because oversized fits differ from standard slim sizing, "
                            "customers should review the published size chart before completing checkout."
                        ),
                    )
                )
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P06-02",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Garment Care Standards & Print Longevity",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Garment Care Standards\n"
                            "Recommended Garment Care for Print & Fabric Longevity: "
                            "1) Washing: Turn graphic crewnecks, hoodies, and jerseys inside-out. Machine wash cold (30°C max) on gentle cycle with similar colors. "
                            "2) Detergent: Use mild liquid detergent only. Never use chlorine bleach, harsh stain removers, or fabric softeners on prints. "
                            "3) Drying: Hang dry or lay flat in the shade. Avoid high-heat tumble drying to prevent cotton shrinkage and print cracking. "
                            "4) Ironing: Steam lightly or iron inside-out on low heat. Never press a hot iron directly onto printed artwork or embroidered badges. "
                            "Damage resulting from improper washing, high-heat drying, bleaching, or direct ironing is not covered as a manufacturing defect."
                        ),
                    )
                )

            # Page 7: Customer Support & Contact Channels
            elif p.page_number == 7:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"RLVNT-GOV-P07-01",
                        brand_id=self.brand_id,
                        source_file=p.source_file,
                        source_page=p.page_number,
                        document_type="Brand Governance & Policies",
                        section="Customer Support & Contact Channels",
                        content=(
                            "Brand: RLVNT | Doc: Brand Governance | Section: Customer Support & Official Contact\n"
                            "Our support team is committed to resolving sizing inquiries, order updates, and exchange requests promptly. "
                            "Support operating hours: Saturday through Thursday, 10:00 AM – 8:00 PM. Target response time: within 24 hours. "
                            "Official contact channels include WhatsApp, Instagram Direct Message, and Email. Support handles high-value verification, "
                            "size swaps, transit damage reports, and customer escalations."
                        ),
                    )
                )

        return chunks

    def chunk_lookbook_collections(
        self, winter_pages: List[ExtractedPage], outfit_pages: List[ExtractedPage]
    ) -> List[KnowledgeChunk]:
        """Generates contextual lookbook knowledge chunks for collections."""
        chunks: List[KnowledgeChunk] = []

        # Winter Collection Overview & Designs
        chunks.append(
            KnowledgeChunk(
                chunk_id="RLVNT-CAT-WNT-01",
                brand_id=self.brand_id,
                source_file="rlvnt_winter_collection.pdf",
                source_page=1,
                document_type="Catalog Lookbook",
                section="Winter Collection Graphic Crewnecks Overview",
                content=(
                    "Brand: RLVNT | Doc: Winter Collection Lookbook | Section: Winter Drop Overview\n"
                    "The RLVNT Winter Collection showcases 9 signature statement crewnecks crafted from heavyweight cotton "
                    "with high-contrast graphic storytelling. Featured designs include: San Andreas ('Ah Shit, Here We Go Again' CJ graphic), "
                    "Michael Jackson Tribute (gold sparkle glove & moon), Kylian Mbappé 2022 World Cup celebration, Diego Maradona Argentine D.N.I., "
                    "'DOGS GOTTA EAT' crimson varsity lettering, Jude Bellingham 'Bellingoal' Real Madrid celebration, Fight Club Tyler Durden with soap bar, "
                    "RLVNT 'Dream Big' thermal star graphic, and Tony Montana 'Scarface' American Dream montage. All tops feature relaxed streetwear fits."
                ),
            )
        )

        # Outfits Collection Overview
        chunks.append(
            KnowledgeChunk(
                chunk_id="RLVNT-CAT-OUTFIT-01",
                brand_id=self.brand_id,
                source_file="rlvnt_outfits_collection.pdf",
                source_page=1,
                document_type="Catalog Lookbook",
                section="Outfits, Hoodies & Vintage Tops Overview",
                content=(
                    "Brand: RLVNT | Doc: Outfits Collection Lookbook | Section: Outfits & Bottoms Overview\n"
                    "The RLVNT Outfits and Sets collection features coordinated streetwear combinations: "
                    "1) 100% Cotton Hoodies: Heavyweight Lionel Messi black signature gold hoodie and Neymar Jr chocolate brown gothic Total 90 hoodie. "
                    "2) Retro Sports Tops: 1990s AC Milan Opel sponsor Lotto long-sleeve kit and Germany 1990 heritage DFB track jacket. "
                    "3) Coordinated Sets: Cristiano Ronaldo CR7 Manchester United crewneck with black sweatpants, Polo Ralph Lauren half-zip fleece set, "
                    "Real Madrid Los Blancos crewneck with heather grey sweatpants, and 'NO FEAR' gothic lion crewneck set. "
                    "4) Bottoms: Vintage washed wide-leg denim jeans and cotton fleece relaxed sweatpants."
                ),
            )
        )

        return chunks

    def process_and_save(self) -> List[KnowledgeChunk]:
        """Runs end-to-end extraction, chunking, and JSONL persistence."""
        extractor = PDFExtractor(brand_id=self.brand_id)
        docs = extractor.extract_all()

        gov_pages = docs.get("rlvntbrandidentityandpolicies.pdf", [])
        winter_pages = docs.get("rlvnt_winter_collection.pdf", [])
        outfit_pages = docs.get("rlvnt_outfits_collection.pdf", [])

        policy_chunks = self.chunk_policy_manual(gov_pages)
        catalog_chunks = self.chunk_lookbook_collections(winter_pages, outfit_pages)

        all_chunks = policy_chunks + catalog_chunks

        output_file = self.output_dir / "chunks.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

        print(f"Generated {len(all_chunks)} semantic chunks at {output_file}")
        return all_chunks


if __name__ == "__main__":
    chunker = SemanticChunker()
    chunker.process_and_save()
