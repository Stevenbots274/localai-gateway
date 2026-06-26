"""Schemas mirroring OpenAI API formats."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union


class ChatMessage(BaseModel):
    role: str = Field(...)
    content: Union[str, List[Dict[str, Any]]] = Field(...)
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(...)
    messages: List[ChatMessage] = Field(...)
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    top_p: Optional[float] = Field(1.0, ge=0, le=1)
    stream: Optional[bool] = Field(False)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(0, ge=-2, le=2)
    seed: Optional[int] = None
    user: Optional[str] = None


class EmbeddingRequest(BaseModel):
    model: str = Field(...)
    input: Union[str, List[str]] = Field(...)
    encoding_format: Optional[str] = Field("float")
    dimensions: Optional[int] = None
    user: Optional[str] = None


class ImageGenerationRequest(BaseModel):
    model: str = Field(...)
    prompt: str = Field(..., min_length=1, max_length=32000)
    n: Optional[int] = Field(1, ge=1, le=10)
    size: Optional[str] = Field("1024x1024")
    quality: Optional[str] = Field("standard")
    style: Optional[str] = Field("vivid")
    response_format: Optional[str] = Field("b64_json")
    user: Optional[str] = None


class AudioTranscriptionRequest(BaseModel):
    model: str = Field(...)
    file: bytes = Field(...)
    language: Optional[str] = None
    prompt: Optional[str] = None
    response_format: Optional[str] = Field("json")
    temperature: Optional[float] = Field(0.0)
    timestamp_granularities: Optional[List[str]] = None


class TextToSpeechRequest(BaseModel):
    model: str = Field(...)
    input: str = Field(..., min_length=1, max_length=4096)
    voice: Optional[str] = Field("alloy")
    response_format: Optional[str] = Field("mp3")
    speed: Optional[float] = Field(1.0, ge=0.25, le=4.0)


class LocalAIModelRequest(BaseModel):
    """LocalAI model management."""
    id: str
    name: str
    object: str = "model"
    owned_by: str = "localai"
    permission: List[Dict[str, Any]] = []
