import fitz
import io
import re
import spacy
from collections import defaultdict
import subprocess

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

PII_PATTERNS = {"EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b","PHONE": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b","SSN": r"\b\d{3}-\d{2}-\d{4}\b"}
NER_LABELS = {"PERSON", "GPE", "ORG", "LOC"}
def redact_pdf_bytes(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    redacted_count = defaultdict(int)
    for page in doc:
        text = page.get_text("text")
        for label, pattern in PII_PATTERNS.items():
            for match in re.finditer(pattern, text):
                for rect in page.search_for(match.group()):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                redacted_count[label] += 1
        spacy_doc = nlp(text)
        for ent in spacy_doc.ents:
            if ent.label_ in NER_LABELS:
                for rect in page.search_for(ent.text):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                redacted_count[ent.label_] += 1
        page.apply_redactions()
    out_stream = io.BytesIO()
    doc.save(out_stream, garbage=4, deflate=True)
    doc.close()
    summary = ", ".join(f"{k}: {v}" for k, v in redacted_count.items())
    return out_stream.getvalue(), summary