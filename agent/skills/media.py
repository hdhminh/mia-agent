from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _run_gateway_tool, _normalize_instruction


def get_media_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool("image_ocr")
    def image_ocr_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Run OCR on an attached image."""
        text = _normalize_instruction("media", "ocr anh", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.image_ocr",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "photo",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("image_describe")
    def image_describe_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Describe an attached image."""
        text = _normalize_instruction("media", "mo ta anh", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.image_describe",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "photo",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("image_extract_fields")
    def image_extract_fields_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Extract structured fields from an image."""
        text = _normalize_instruction("media", "trich thong tin anh", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.image_extract_fields",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "photo",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("document_extract_text")
    def document_extract_text_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Extract text from a PDF, Word file, or text document."""
        text = _normalize_instruction("media", "trich text tai lieu", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.document_extract_text",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "document",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("document_summarize")
    def document_summarize_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Summarize a PDF, Word file, or text document."""
        text = _normalize_instruction("media", "tom tat tai lieu", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.document_summarize",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "document",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("document_search_answer")
    def document_search_answer_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        question: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Answer a question from a PDF, Word file, or text document."""
        text = _normalize_instruction("media", "hoi tai lieu", instruction or question or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.document_search_answer",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "document",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "question": question.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("document_extract_fields")
    def document_extract_fields_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Extract structured fields from a document."""
        text = _normalize_instruction("media", "trich truong tai lieu", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.document_extract_fields",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "document",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("audio_transcribe")
    def audio_transcribe_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Transcribe an audio file or voice note."""
        text = _normalize_instruction("media", "chep loi am thanh", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.audio_transcribe",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "audio",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "language": language.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("audio_summarize")
    def audio_summarize_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Summarize an audio file or voice note."""
        text = _normalize_instruction("media", "tom tat am thanh", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.audio_summarize",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "audio",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "language": language.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("video_transcribe")
    def video_transcribe_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Transcribe speech from a video file."""
        text = _normalize_instruction("media", "chep loi video", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.video_transcribe",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "video",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "language": language.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("video_summarize")
    def video_summarize_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        attachment_kind: str = "",
        language: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Summarize a video file."""
        text = _normalize_instruction("media", "tom tat video", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "media.video_summarize",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "attachmentKind": attachment_kind.strip() or "video",
                "hasAttachment": bool(file_id.strip() or file_name.strip()),
                "language": language.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
            },
            runtime,
        )

    @tool("tts_speak")
    def tts_speak_tool(
        text: str,
        voice: str = "",
        model: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Turn text into spoken audio."""
        spoken_text = _normalize_instruction("media", "doc thanh giong noi", text)
        return _run_gateway_tool(
            tool_gateway,
            "media.tts_speak",
            {
                "text": spoken_text,
                "instruction": spoken_text,
                "prompt": spoken_text,
                "voice": voice.strip(),
                "model": model.strip(),
                "hasAttachment": False,
            },
            runtime,
        )

    return [
        image_ocr_tool,
        image_describe_tool,
        image_extract_fields_tool,
        document_extract_text_tool,
        document_summarize_tool,
        document_search_answer_tool,
        document_extract_fields_tool,
        audio_transcribe_tool,
        audio_summarize_tool,
        video_transcribe_tool,
        video_summarize_tool,
        tts_speak_tool,
    ]
