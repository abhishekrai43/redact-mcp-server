from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio
import uuid
import json

app = FastAPI()

active_clients = {}

class ToolExecutionRequest(BaseModel):
    id: str
    method: str
    params: dict

@app.get("/sse")
async def sse_endpoint(request: Request):
    client_id = str(uuid.uuid4())

    async def event_generator():
        # Send 'initialize' response
        yield f"data: {json.dumps({ 'jsonrpc': '2.0', 'method': 'initialize', 'params': {} })}\n\n"

        # Send tool list
        tool_list = {
            "jsonrpc": "2.0",
            "method": "tool/list",
            "params": {
                "tools": [
                    {
                        "name": "redact_pdf",
                        "description": "Redacts PDF with AI retry",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "pdf_base64": {"type": "string"},
                                "retry_with_ai": {"type": "boolean"}
                            },
                            "required": ["pdf_base64"]
                        },
                        "output_schema": {
                            "type": "object",
                            "properties": {
                                "redacted_pdf_base64": {"type": "string"},
                                "summary": {"type": "string"},
                                "ai_retry_triggered": {"type": "boolean"}
                            },
                            "required": ["redacted_pdf_base64", "summary", "ai_retry_triggered"]
                        }
                    }
                ]
            }
        }
        yield f"data: {json.dumps(tool_list)}\n\n"

        # Keep client alive
        try:
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(30)
        finally:
            active_clients.pop(client_id, None)

    active_clients[client_id] = asyncio.Queue()
    return EventSourceResponse(event_generator(), media_type="text/event-stream")

@app.post("/messages")
async def receive_message(msg: ToolExecutionRequest):
    if msg.method == "tool/execute" and msg.params["tool_name"] == "redact_pdf":
        # Perform fake redaction logic
        response = {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {
                "redacted_pdf_base64": msg.params["input"]["pdf_base64"],
                "summary": "Redacted dummy content",
                "ai_retry_triggered": msg.params["input"].get("retry_with_ai", False)
            }
        }
        # Find the client and push response
        for q in active_clients.values():
            await q.put(json.dumps(response))
        return {"status": "ok"}

    return {"error": "unsupported method"}
