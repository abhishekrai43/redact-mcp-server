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
    if msg.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {}
        }

    if msg.method == "tool/list":
        return {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {
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


    if msg.method == "tool/execute" and msg.params["tool_name"] == "redact_pdf":
        response = {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {
                "redacted_pdf_base64": msg.params["input"]["pdf_base64"],
                "summary": "Redacted dummy content",
                "ai_retry_triggered": msg.params["input"].get("retry_with_ai", False)
            }
        }

        for queue in client_queues.values():
            await queue.put(response)

        return {"status": "ok"}

    return {
        "jsonrpc": "2.0",
        "id": msg.id,
        "error": {
            "code": -32601,
            "message": f"Method '{msg.method}' not implemented"
        }
    }

