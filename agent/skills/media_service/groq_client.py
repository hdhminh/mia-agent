from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any

from agent.i18n import t
import httpx


@dataclass(frozen=True)
class GroqTranscriptionResult:
    text: str
    data: dict[str, Any]


class GroqMediaClient:
    def __init__(self, *, api_key: str, base_url: str = "https://api.groq.com/openai/v1") -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        raw = str(content or "").strip()
        candidates = [raw]

        fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
        candidates.extend(item.strip() for item in fenced if item.strip())

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(raw[start : end + 1].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
        return {"summary": raw, "fields": {}}

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, action: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text.strip()
            message = f"Groq {action} failed ({response.status_code})"
            if body:
                compact = " ".join(body.split())
                message += f": {compact[:240]}"
            raise RuntimeError(message) from exc

    def describe_image(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        model: str,
        prompt: str = "",
    ) -> str:
        if not self.enabled:
            raise RuntimeError("GROQ_API_KEY is required for image description.")

        data_url = f"data:{mime_type or 'image/png'};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        user_prompt = prompt.strip() or t(
            "skills.groq_image_describe_user",
            default=(
                "Hãy mô tả bức ảnh này bằng tiếng Việt theo kiểu ngắn gọn nhưng đủ ý. "
                "Ưu tiên nêu đối tượng chính, bối cảnh, hành động hoặc cảm xúc nổi bật. "
                "Nếu có chữ trong ảnh, hãy nhắc cả phần chữ đáng chú ý."
            ),
        )
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": t(
                        "skills.groq_image_describe_system",
                        default=(
                            "Bạn là trợ lý mô tả ảnh. Trả lời tự nhiên bằng tiếng Việt, "
                            "rõ ý, không bịa, không lan man, phù hợp để đọc trong khung chat."
                        ),
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response, action="image description")
            data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()

    def extract_image_fields(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        model: str,
        prompt: str = "",
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("GROQ_API_KEY is required for image field extraction.")

        data_url = f"data:{mime_type or 'image/png'};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        user_prompt = prompt.strip() or t(
            "skills.groq_image_extract_user",
            default=(
                "Hãy trích ra các trường dữ liệu quan trọng từ ảnh. "
                "Chỉ trả về JSON hợp lệ với hai khóa: summary và fields. "
                "summary nên ngắn gọn, còn fields là object chứa các trường có thể nhận ra như name, date, amount, id, email, phone, url hoặc các key phù hợp."
            ),
        )
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": t(
                        "skills.groq_image_extract_system",
                        default=(
                            "Bạn là công cụ trích xuất dữ liệu từ ảnh. "
                            "Luôn trả về JSON hợp lệ, không kèm markdown hay giải thích ngoài JSON."
                        ),
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response, action="image field extraction")
            data = response.json()
        content = str(data["choices"][0]["message"]["content"]).strip()
        return self._parse_json_content(content)

    def transcribe_audio(
        self,
        *,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        model: str,
        language: str = "",
        prompt: str = "",
        response_format: str = "verbose_json",
    ) -> GroqTranscriptionResult:
        if not self.enabled:
            raise RuntimeError("GROQ_API_KEY is required for speech-to-text.")

        files = {"file": (file_name or "audio.bin", file_bytes, mime_type or "application/octet-stream")}
        data = {
            "model": model,
            "response_format": response_format,
        }
        if language.strip():
            data["language"] = language.strip()
        if prompt.strip():
            data["prompt"] = prompt.strip()

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
            )
            self._raise_for_status(response, action="speech-to-text")
            payload = response.json()

        text = str(payload.get("text") or "").strip()
        return GroqTranscriptionResult(text=text, data=payload)

    def speak(
        self,
        *,
        text: str,
        model: str,
        voice: str,
        response_format: str = "mp3",
    ) -> tuple[bytes, str]:
        if not self.enabled:
            raise RuntimeError("GROQ_API_KEY is required for text-to-speech.")

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/audio/speech",
                headers=self._headers(),
                json=payload,
            )
            self._raise_for_status(response, action="text-to-speech")
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip() or "audio/mpeg"
            return response.content, content_type
