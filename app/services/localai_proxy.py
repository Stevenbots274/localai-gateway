"""Service for proxying requests to LocalAI backend."""
import httpx
import time
from typing import Optional, Any, Dict
from app.core.config import settings

# Shared httpx client
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(300.0, connect=30.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    http2=True,
)


class LocalAIProxy:
    """Proxy service for LocalAI backend."""

    BASE_URL = settings.localai_base_url
    HEADERS = settings.localai_headers

    @staticmethod
    async def request(
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[dict] = None,
        content: Optional[bytes] = None,
        headers: Optional[dict] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Make a request to LocalAI."""
        url = f"{LocalAIProxy.BASE_URL}{endpoint}"
        req_headers = dict(LocalAIProxy.HEADERS)
        if headers:
            req_headers.update(headers)

        if method == "GET":
            return await http_client.get(url, params=params, headers=req_headers)
        elif method == "POST":
            if files:
                return await http_client.post(url, data=json_data, files=files, headers=req_headers)
            elif json_data:
                return await http_client.post(url, json=json_data, headers=req_headers)
            elif content:
                return await http_client.post(url, content=content, headers=req_headers)
            else:
                return await http_client.post(url, headers=req_headers)
        elif method == "DELETE":
            return await http_client.delete(url, headers=req_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """Check LocalAI health."""
        try:
            response = await http_client.get(
                f"{LocalAIProxy.BASE_URL}/readyz",
                timeout=10.0
            )
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "status_code": response.status_code,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    async def list_models() -> Dict[str, Any]:
        """List available models from LocalAI."""
        response = await LocalAIProxy.request("GET", "/v1/models")
        return response.json()

    @staticmethod
    def extract_token_usage(response_data: dict) -> tuple[int, int, int]:
        """Extract token usage from response."""
        usage = response_data.get("usage", {})
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", prompt + completion)
        return prompt, completion, total


localai_proxy = LocalAIProxy()
