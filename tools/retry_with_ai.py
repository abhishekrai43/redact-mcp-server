import fitz
import io
from fpdf import FPDF
import openai

def run_ai_retry_redaction(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a PII removal agent."},
            {"role": "user", "content": f"Redact all PII from this document:\n{text}"}
        ]
    )
    cleaned_text = response.choices[0].message.content
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in cleaned_text.splitlines():
        pdf.multi_cell(0, 10, line)
    out_stream = io.BytesIO()
    pdf.output(out_stream)
    return out_stream.getvalue(), "AI redaction applied"