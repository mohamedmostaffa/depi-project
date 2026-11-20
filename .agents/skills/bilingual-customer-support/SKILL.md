---
name: bilingual-customer-support
description: Handling Egyptian Arabic, MSA, and English customer interactions, including Arabic-Indic digit normalization, slang recognition, and culturally grounded responses.
---

# Bilingual Customer Support Skill

## Purpose
This skill manages linguistic nuances for the Egyptian and MENA e-commerce market, supporting English, Modern Standard Arabic (MSA), Egyptian Arabic (العامية المصرية), and Franco-Arabic ("Arabizi").

## When to Activate
- Developing the understanding pipeline (`src/agents/orchestrator.py`, `src/prompts/templates/intent_understanding.j2`).
- Normalizing Arabic inputs (digits, diacritics, spelling variations).
- Evaluating naturalness and dialect consistency in customer-facing replies.

## Technical Instructions
1. **Input Normalization:**
   - Translate Eastern Arabic-Indic digits (٠, ١, ٢, ٣, ٤, ٥, ٦, ٧, ٨, ٩) to ASCII digits (0–9) before entity extraction or policy checks.
   - Normalize common Arabic orthographic variations (أ, إ, آ $\rightarrow$ ا; ة $\rightarrow$ ه when appropriate for fuzzy matching).
2. **Dialect Detection & Mirroring:**
   - Differentiate Egyptian Arabic from MSA using dialect marker words (e.g., عايز, مش, علشان, دلوقتي, إزاي, كده, فين).
   - If the customer uses Egyptian Arabic, respond in natural, friendly Egyptian Arabic matching the RLVNT streetwear identity. Do NOT use stiff, formal bureaucratic MSA for street apparel inquiries.
3. **Product & Technical Terms:**
   - Preserve core streetwear terms (Hoodie, Oversized, Crewneck, Drop, Collection) in their recognizable transliterated or Latin forms (e.g. هودي أو كرو-نيك أو أوفرسايز) as used in Egyptian fashion culture.

## Testing & Validation Checklist
- [ ] Arabic digit strings ("١٤ يوم", "طلب رقم ١٠٤٢") parse accurately into integers.
- [ ] Separate evaluation test sets for MSA and Egyptian Arabic.
- [ ] Egyptian Arabic inquiries receive responses scored as culturally and tonally natural by native speakers.
