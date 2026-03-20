"""
WHY: Gemini CLI's Gemma Model Router requires a local HTTP endpoint at
     localhost:9379 that speaks the Gemini REST API format.  Ollama exposes
     a different API (OpenAI-compat + its own /api/chat).  This shim bridges
     the two: it accepts Gemini-format generateContent requests and rewrites
     them as Ollama chat requests, then reformats the response back.

     Endpoint: POST /v1beta/models/{model}:generateContent
     Calls:    POST http://localhost:11434/api/chat  (stream=false)

     Model name mapping: Gemini URL slugs use hyphens (gemma3-1b) while
     Ollama uses colons (gemma3:1b).  The shim converts the last '-' before a
     digit segment to ':' to handle the common case.  Override via
     OLLAMA_MODEL env var for non-standard names.
"""

from __future__ import annotations

import os
import re
import logging
import uvicorn
import httpx

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

HOST = os.getenv("SHIM_HOST", "127.0.0.1")
PORT = int(os.getenv("SHIM_PORT", "9379"))
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

logging.basicConfig(level=LOG_LEVEL.upper())
log = logging.getLogger("gemini-shim")

app = FastAPI(title="ollama-gemini-shim", version="1.0.0")


def _ollama_model(gemini_slug: str) -> str:
    """Convert a Gemini URL model slug to an Ollama model name.

    gemma3-1b  -> gemma3:1b
    gemma-2-2b -> gemma2:2b  (last hyphen before digit run)
    gemma3     -> gemma3      (no digit suffix, leave as-is)
    """
    override = os.getenv("OLLAMA_MODEL")
    if override:
        return override
    # Replace the last hyphen that precedes a digit sequence with ':'
    return re.sub(r"-(\d)", r":\1", gemini_slug, count=1)


def _parts_to_text(parts: list[dict]) -> str:
    """Concatenate all 'text' values from a Gemini parts array."""
    return "".join(p.get("text", "") for p in parts if "text" in p)


def _gemini_contents_to_messages(contents: list[dict]) -> list[dict]:
    """Map Gemini contents[] -> Ollama messages[].

    Gemini role 'model' -> Ollama role 'assistant'.
    """
    messages = []
    for item in contents:
        role = item.get("role", "user")
        ollama_role = "assistant" if role == "model" else role
        text = _parts_to_text(item.get("parts", []))
        messages.append({"role": ollama_role, "content": text})
    return messages


def _wrap_ollama_response(ollama_resp: dict) -> dict:
    """Wrap an Ollama /api/chat response in the Gemini generateContent envelope."""
    content_text = ollama_resp.get("message", {}).get("content", "")
    done_reason = ollama_resp.get("done_reason", "stop").upper()
    # Gemini finish reasons: STOP, MAX_TOKENS, SAFETY, RECITATION, OTHER
    finish_reason = "STOP" if done_reason == "STOP" else "OTHER"
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": content_text}],
                    "role": "model",
                },
                "finishReason": finish_reason,
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": ollama_resp.get("prompt_eval_count", 0),
            "candidatesTokenCount": ollama_resp.get("eval_count", 0),
        },
    }


@app.get("/v1beta/models")
async def list_models() -> JSONResponse:
    """Proxy Ollama model list into a Gemini-shaped response."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Ollama unreachable: {exc}") from exc
    models = r.json().get("models", [])
    gemini_models = [
        {"name": f"models/{m['name']}", "displayName": m["name"]}
        for m in models
    ]
    return JSONResponse({"models": gemini_models})


@app.post("/v1beta/models/{model_id:path}")
async def generate_content(model_id: str, request: Request) -> JSONResponse:
    """Accept a Gemini generateContent request and proxy it to Ollama.

    URL pattern: /v1beta/models/{model}:generateContent
    The FastAPI path captures everything after /v1beta/models/, including the
    ':generateContent' suffix.  We strip the action suffix to get the model slug.
    """
    # Strip the trailing ':action' suffix (e.g. ':generateContent', ':countTokens').
    # model_id may contain colons already (e.g. 'gemma3:1b:generateContent' when
    # the Gemini CLI URL slug uses the Ollama colon notation directly).
    # API verb names are camelCase and start with a lowercase letter; version tags
    # (e.g. '1b', 'latest') do not.  rsplit peels off only the final segment.
    parts = model_id.rsplit(":", 1)
    if len(parts) == 2 and parts[1] and parts[1][0].islower():
        slug = parts[0]   # e.g. 'gemma3:1b'
    else:
        slug = model_id   # no recognised action suffix
    ollama_model_name = _ollama_model(slug)

    body = await request.json()
    contents = body.get("contents", [])
    if not contents:
        raise HTTPException(400, "contents array is required")

    messages = _gemini_contents_to_messages(contents)

    # Generation config (optional, best-effort mapping)
    gen_cfg = body.get("generationConfig", {})
    ollama_options: dict = {}
    if "temperature" in gen_cfg:
        ollama_options["temperature"] = gen_cfg["temperature"]
    if "maxOutputTokens" in gen_cfg:
        ollama_options["num_predict"] = gen_cfg["maxOutputTokens"]
    if "topP" in gen_cfg:
        ollama_options["top_p"] = gen_cfg["topP"]
    if "topK" in gen_cfg:
        ollama_options["top_k"] = gen_cfg["topK"]

    payload: dict = {
        "model": ollama_model_name,
        "messages": messages,
        "stream": False,
    }
    if ollama_options:
        payload["options"] = ollama_options

    log.debug("POST /api/chat model=%s messages=%d", ollama_model_name, len(messages))

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.error("Ollama error: %s %s", exc.response.status_code, exc.response.text)
            raise HTTPException(502, f"Ollama returned {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Ollama unreachable: {exc}") from exc

    return JSONResponse(_wrap_ollama_response(r.json()))


if __name__ == "__main__":
    log.info("Starting ollama-gemini-shim on %s:%d -> %s", HOST, PORT, OLLAMA_BASE)
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL)
