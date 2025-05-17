from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
from tools.redact_pdf import redact_pdf_bytes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RedactRequest(BaseModel):
    pdf_base64: str
    retry_with_ai: bool = False

class RedactResponse(BaseModel):
    redacted_pdf_base64: str
    summary: str
    ai_retry_triggered: bool

@app.post("/tools/redact_pdf", response_model=RedactResponse)
def redact_pdf_handler(request: RedactRequest):
    try:
        pdf_bytes = base64.b64decode(request.pdf_base64)
        redacted_bytes, summary = redact_pdf_bytes(pdf_bytes)

        ai_retry_triggered = False
        if request.retry_with_ai:
            from tools.retry_with_ai import run_ai_retry_redaction
            redacted_bytes, summary = run_ai_retry_redaction(redacted_bytes)
            ai_retry_triggered = True

        encoded_output = base64.b64encode(redacted_bytes).decode('utf-8')
        return {
            "redacted_pdf_base64": encoded_output,
            "summary": summary,
            "ai_retry_triggered": ai_retry_triggered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
