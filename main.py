from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio
import uuid
import json

app = FastAPI()
client_queues = {}

class ToolExecutionRequest(BaseModel):
    id: str
    method: str
    params: dict

@app.get("/sse")
async def sse_endpoint(request: Request):
    client_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    client_queues[client_id] = queue

    async def event_generator():
        try:
            # Immediately send initialize and tool/list messages in correct format
            yield json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {}
            }) + "\n\n"

            yield json.dumps({
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
            }) + "\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield json.dumps(message) + "\n\n"
                except asyncio.TimeoutError:
                    continue
        finally:
            client_queues.pop(client_id, None)

    return EventSourceResponse(event_generator(), media_type="text/event-stream")

@app.post("/messages")
async def receive_message(msg: ToolExecutionRequest):
    if msg.method == "tool/execute" and msg.params["tool_name"] == "redact_pdf":
        # Dummy redaction logic
        response = {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {
                "redacted_pdf_base64": msg.params["input"]["pdf_base64"],
                "summary": "Redacted dummy content",
                "ai_retry_triggered": msg.params["input"].get("retry_with_ai", False)
            }
        }

        # Send response to all connected clients (or track by client_id if you want)
        for queue in client_queues.values():
            await queue.put(response)

        return {"status": "ok"}

    return {"error": "Unsupported method"}
