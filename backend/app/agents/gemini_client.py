import json
from typing import TypeVar, Type
from pydantic import BaseModel
from app.config import settings
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("thats-a-wrap-backend.ai")

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.gemini_api_key)
        self.client = None
        if self.enabled:
            from google import genai
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def structured(self, prompt: str, schema: Type[T], fallback: T) -> T:
        with tracer.start_as_current_span("gemini_structured_generation") as span:
            span.set_attribute("operation.type", "ai_generation")
            span.set_attribute("ai.provider", "google_gemini")
            span.set_attribute("ai.model", settings.gemini_model)
            span.set_attribute("ai.schema", schema.__name__)
            span.set_attribute("ai.mode", "gemini" if self.client else "deterministic-fallback")
            if not self.client:
                span.set_attribute("ai.fallback", True)
                span.set_attribute("operation.status", "success")
                return fallback
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
                if getattr(response, "parsed", None) is not None:
                    result = schema.model_validate(response.parsed)
                else:
                    result = schema.model_validate_json(response.text)
                span.set_attribute("ai.fallback", False)
                span.set_attribute("operation.status", "success")
                return result
            except Exception as exc:
                # Gemini failures intentionally fall back so the production demo remains usable,
                # but the failure is still visible in the trace.
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("operation.status", "degraded")
                span.set_attribute("ai.fallback", True)
                span.set_attribute("error.type", type(exc).__name__)
                return fallback

    @property
    def mode(self) -> str:
        return "gemini" if self.enabled else "deterministic-fallback"
