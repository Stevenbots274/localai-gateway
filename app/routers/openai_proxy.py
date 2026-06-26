"""OpenAI-compatible API proxy routes to LocalAI backend."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any
import time

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_api_key
from app.models.api_key import APIKey
from app.services.api_key_service import api_key_service
from app.services.usage_service import usage_service
from app.services.localai_proxy import localai_proxy

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


async def proxy_to_localai(
    request: Request,
    db: AsyncSession,
    api_key: APIKey,
    endpoint: str,
    method: str = "GET",
    body: Optional[Any] = None,
    params: Optional[dict] = None,
    files: Optional[dict] = None,
    stream: bool = False,
    content_type: Optional[str] = None
) -> Response:
    """Proxy a request to LocalAI HTTP server."""

    url = f"{settings.localai_base_url}{endpoint}"
    headers = dict(settings.localai_headers)

    if content_type:
        headers["Content-Type"] = content_type
    elif body and not files:
        headers["Content-Type"] = "application/json"

    start_time = time.time()
    model_name = None
    status_code = None
    error_msg = None
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        if isinstance(body, dict) and "model" in body:
            model_name = body["model"]

        response = await localai_proxy.request(
            method=method, endpoint=endpoint,
            json_data=body if isinstance(body, dict) else None,
            params=params, files=files,
            content=body if isinstance(body, bytes) else None,
            headers=headers, stream=stream
        )

        status_code = response.status_code
        latency = (time.time() - start_time) * 1000

        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                resp_data = response.json()
                if "usage" in resp_data:
                    usage = resp_data["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
            except Exception:
                pass

        # Log usage
        await api_key_service.increment_usage(db, api_key.id, total_tokens)
        await usage_service.log_request(
            db=db,
            api_key_id=api_key.id if api_key.id != "admin" else None,
            endpoint=endpoint, method=method, model=model_name,
            status_code=status_code,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            total_tokens=total_tokens, latency_ms=latency,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Handle streaming
        if stream and response.status_code == 200:
            async def stream_generator():
                async for chunk in response.aiter_text():
                    yield chunk
            return StreamingResponse(
                stream_generator(),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="text/event-stream"
            )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() 
                     if k.lower() not in ["content-encoding", "transfer-encoding"]},
            media_type=response.headers.get("content-type", "application/json")
        )

    except Exception as e:
        error_msg = str(e)
        latency = (time.time() - start_time) * 1000
        await usage_service.log_request(
            db=db, api_key_id=api_key.id if api_key.id != "admin" else None,
            endpoint=endpoint, method=method, model=model_name,
            status_code=503, latency_ms=latency,
            client_ip=request.client.host if request.client else None,
            error_message=error_msg,
        )
        raise HTTPException(status_code=503, detail=f"LocalAI error: {error_msg}")


# ============ MODELS ============

@router.get("/models")
async def list_models(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List available models."""
    return await proxy_to_localai(request, db, api_key, "/v1/models")


@router.get("/models/{model_id}")
async def get_model(
    model_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get model details."""
    return await proxy_to_localai(request, db, api_key, f"/v1/models/{model_id}")


# ============ CHAT COMPLETIONS ============

@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Chat completions endpoint."""
    body = await request.json()
    stream = body.get("stream", False)
    return await proxy_to_localai(
        request, db, api_key, "/v1/chat/completions",
        method="POST", body=body, stream=stream
    )


# ============ COMPLETIONS ============

@router.post("/completions")
async def legacy_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Legacy text completions."""
    body = await request.json()
    stream = body.get("stream", False)
    return await proxy_to_localai(
        request, db, api_key, "/v1/completions",
        method="POST", body=body, stream=stream
    )


# ============ EMBEDDINGS ============

@router.post("/embeddings")
async def create_embeddings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create embeddings."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, "/v1/embeddings",
        method="POST", body=body
    )


# ============ AUDIO ============

@router.post("/audio/transcriptions")
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(...),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
    temperature: Optional[float] = Form(0.0),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Audio transcription (STT)."""
    file_content = await file.read()
    files = {"file": (file.filename, file_content, file.content_type)}
    data = {"model": model, "response_format": response_format}
    if language: data["language"] = language
    if prompt: data["prompt"] = prompt
    if temperature is not None: data["temperature"] = str(temperature)

    return await proxy_to_localai(
        request, db, api_key, "/v1/audio/transcriptions",
        method="POST", body=data, files=files
    )


@router.post("/audio/translations")
async def audio_translations(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(...),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
    temperature: Optional[float] = Form(0.0),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Audio translation."""
    file_content = await file.read()
    files = {"file": (file.filename, file_content, file.content_type)}
    data = {"model": model, "response_format": response_format}
    if prompt: data["prompt"] = prompt
    if temperature is not None: data["temperature"] = str(temperature)

    return await proxy_to_localai(
        request, db, api_key, "/v1/audio/translations",
        method="POST", body=data, files=files
    )


@router.post("/audio/speech")
async def text_to_speech(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Text-to-speech (TTS)."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, "/v1/audio/speech",
        method="POST", body=body
    )


# ============ IMAGES ============

@router.post("/images/generations")
async def image_generations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Image generation."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, "/v1/images/generations",
        method="POST", body=body
    )


@router.post("/images/edits")
async def image_edits(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Image editing."""
    form = await request.form()
    files = {}
    data = {}
    for key, value in form.multi_items():
        if hasattr(value, "filename"):
            files[key] = (value.filename, await value.read(), value.content_type)
        else:
            data[key] = value

    return await proxy_to_localai(
        request, db, api_key, "/v1/images/edits",
        method="POST", body=data, files=files
    )


# ============ FILES ============

@router.post("/files")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Upload a file."""
    file_content = await file.read()
    files = {"file": (file.filename, file_content, file.content_type)}
    data = {"purpose": purpose}

    return await proxy_to_localai(
        request, db, api_key, "/v1/files",
        method="POST", body=data, files=files
    )


@router.get("/files")
async def list_files(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List uploaded files."""
    return await proxy_to_localai(request, db, api_key, "/v1/files")


@router.get("/files/{file_id}")
async def get_file(
    file_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get file info."""
    return await proxy_to_localai(request, db, api_key, f"/v1/files/{file_id}")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Delete a file."""
    return await proxy_to_localai(request, db, api_key, f"/v1/files/{file_id}", method="DELETE")


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get file content."""
    return await proxy_to_localai(request, db, api_key, f"/v1/files/{file_id}/content")


# ============ ASSISTANTS ============

@router.post("/assistants")
async def create_assistant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create assistant."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, "/v1/assistants",
        method="POST", body=body
    )


@router.get("/assistants")
async def list_assistants(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List assistants."""
    return await proxy_to_localai(request, db, api_key, "/v1/assistants")


@router.get("/assistants/{assistant_id}")
async def get_assistant(
    assistant_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get assistant."""
    return await proxy_to_localai(request, db, api_key, f"/v1/assistants/{assistant_id}")


@router.post("/assistants/{assistant_id}")
async def modify_assistant(
    assistant_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Modify assistant."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, f"/v1/assistants/{assistant_id}",
        method="POST", body=body
    )


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(
    assistant_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Delete assistant."""
    return await proxy_to_localai(request, db, api_key, f"/v1/assistants/{assistant_id}", method="DELETE")


# ============ THREADS ============

@router.post("/threads")
async def create_thread(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create thread."""
    body = await request.json() if await request.body() else {}
    return await proxy_to_localai(
        request, db, api_key, "/v1/threads",
        method="POST", body=body
    )


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get thread."""
    return await proxy_to_localai(request, db, api_key, f"/v1/threads/{thread_id}")


@router.post("/threads/{thread_id}")
async def modify_thread(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Modify thread."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, f"/v1/threads/{thread_id}",
        method="POST", body=body
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Delete thread."""
    return await proxy_to_localai(request, db, api_key, f"/v1/threads/{thread_id}", method="DELETE")


# ============ THREAD MESSAGES ============

@router.post("/threads/{thread_id}/messages")
async def create_message(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create message in thread."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, f"/v1/threads/{thread_id}/messages",
        method="POST", body=body
    )


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List messages in thread."""
    return await proxy_to_localai(request, db, api_key, f"/v1/threads/{thread_id}/messages")


# ============ THREAD RUNS ============

@router.post("/threads/{thread_id}/runs")
async def create_run(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create run in thread."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, f"/v1/threads/{thread_id}/runs",
        method="POST", body=body
    )


@router.get("/threads/{thread_id}/runs")
async def list_runs(
    thread_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List runs in thread."""
    return await proxy_to_localai(request, db, api_key, f"/v1/threads/{thread_id}/runs")


@router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(
    thread_id: str, run_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get run."""
    return await proxy_to_localai(request, db, api_key, f"/v1/threads/{thread_id}/runs/{run_id}")


@router.post("/threads/{thread_id}/runs/{run_id}")
async def modify_run(
    thread_id: str, run_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Modify run."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, f"/v1/threads/{thread_id}/runs/{run_id}",
        method="POST", body=body
    )


# ============ FINE-TUNING ============

@router.post("/fine_tuning/jobs")
async def create_fine_tuning_job(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Create fine-tuning job."""
    body = await request.json()
    return await proxy_to_localai(
        request, db, api_key, "/v1/fine_tuning/jobs",
        method="POST", body=body
    )


@router.get("/fine_tuning/jobs")
async def list_fine_tuning_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """List fine-tuning jobs."""
    return await proxy_to_localai(request, db, api_key, "/v1/fine_tuning/jobs")


@router.get("/fine_tuning/jobs/{job_id}")
async def get_fine_tuning_job(
    job_id: str, request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Get fine-tuning job."""
    return await proxy_to_localai(request, db, api_key, f"/v1/fine_tuning/jobs/{job_id}")
