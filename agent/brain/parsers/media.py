from __future__ import annotations

from typing import Any

from agent.brain.parsers.common import (
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    _matches_action,
    UPLOAD_ACTION_CUES,
    CREATE_ACTION_CUES,
    SEARCH_ACTION_CUES,
    DELETE_ACTION_CUES,
)

MEDIA_ANALYZE_CUES = (
    "phan tich",
    "phân tích",
    "doc",
    "đọc",
    "xem",
    "mo ta",
    "mô tả",
    "tom tat",
    "tóm tắt",
    "trich",
    "trích",
    "ocr",
    "chuyen loi",
    "chuyển lời",
    "chep loi",
    "chép lời",
    "transcribe",
    "summary",
    "speak",
    "voice",
    "đọc thành giọng nói",
    "noi lai",
    "nói lại",
)

IMAGE_ACTION_CUES = (
    "anh",
    "ảnh",
    "photo",
    "picture",
    "screenshot",
    "ocr",
    "mo ta anh",
    "mô tả ảnh",
    "trich chu",
    "trích chữ",
    "trich thong tin",
    "trích thông tin",
    "lay thong tin",
    "lấy thông tin",
    "bang gia",
    "hóa đơn",
    "hoa don",
)

DOCUMENT_ACTION_CUES = (
    "pdf",
    "word",
    "docx",
    "tai lieu",
    "tài liệu",
    "van ban",
    "văn bản",
    "hop dong",
    "hợp đồng",
    "file",
    "extract",
    "trich truong",
    "trích trường",
    "search answer",
    "hoi dap",
    "hỏi đáp",
)

AUDIO_ACTION_CUES = (
    "audio",
    "am thanh",
    "âm thanh",
    "voice note",
    "voice",
    "ghi am",
    "ghi âm",
    "chep loi",
    "chép lời",
    "transcribe",
)

VIDEO_ACTION_CUES = (
    "video",
    "clip",
    "phim",
    "recording",
    "record",
    "subtitle",
    "phu de",
    "phụ đề",
    "chuyen loi",
    "chuyển lời",
)

VOICE_OUTPUT_CUES = (
    "doc thanh giong noi",
    "đọc thành giọng nói",
    "doc to len",
    "đọc to lên",
    "noi lai",
    "nói lại",
    "voice",
    "phat am",
    "phát âm",
    "doc cho minh nghe",
    "đọc cho mình nghe",
)


def _metadata_attachment_kind(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""
    return normalize_query_text(str(metadata.get("attachmentKind") or metadata.get("attachment_kind") or ""))


def _metadata_has_attachment(metadata: dict[str, Any] | None) -> bool:
    if not metadata:
        return False
    return bool(metadata.get("hasAttachment") or metadata.get("has_attachment"))


def _infer_media_hint(normalized: str, metadata: dict[str, Any] | None, help_request: bool) -> tuple[str, bool]:
    attachment_kind = _metadata_attachment_kind(metadata)
    has_attachment = _metadata_has_attachment(metadata)
    if help_request:
        return "", False

    voice_output = any(keyword_matches(normalized, cue) for cue in VOICE_OUTPUT_CUES)
    if voice_output:
        return "tts_speak", True

    if not has_attachment and attachment_kind not in {"photo", "document", "video", "audio"}:
        return "", False

    is_save_request = _matches_action(normalized, UPLOAD_ACTION_CUES) or any(
        keyword_matches(normalized, cue) for cue in ("luu", "lưu", "tai len", "tải lên", "save", "store")
    )
    if is_save_request:
        return "drive_upload_file", True

    is_photo = attachment_kind == "photo" or any_keyword_matches(normalized, IMAGE_ACTION_CUES)
    is_document = attachment_kind == "document" or any_keyword_matches(normalized, DOCUMENT_ACTION_CUES)
    is_audio = attachment_kind in {"audio"} or any_keyword_matches(normalized, AUDIO_ACTION_CUES)
    is_video = attachment_kind == "video" or any_keyword_matches(normalized, VIDEO_ACTION_CUES)

    if is_photo:
        if any(keyword_matches(normalized, cue) for cue in ("phan tich", "phân tích", "analyse", "analyze", "analysis", "xem", "mo ta", "mô tả")):
            return "image_describe", True
        if any(keyword_matches(normalized, cue) for cue in ("trich chu", "trích chữ", "ocr", "doc", "đọc", "scan")):
            return "image_ocr", True
        if any(keyword_matches(normalized, cue) for cue in ("mo ta", "mô tả", "describe", "anh co gi", "ảnh có gì", "what is in")):
            return "image_describe", True
        if any(keyword_matches(normalized, cue) for cue in ("trich thong tin", "trích thông tin", "lay thong tin", "lấy thông tin", "fields", "truong du lieu", "trường dữ liệu")):
            return "image_extract_fields", True
        if _matches_action(normalized, CREATE_ACTION_CUES) or _matches_action(normalized, SEARCH_ACTION_CUES):
            # Wait, CREATE_ACTION_CUES is not imported. Let's see if we should import it or if we can define/import it.
            # Ah, yes! We should import CREATE_ACTION_CUES and SEARCH_ACTION_CUES from parsers.common! Let's update the import statement at the top.
            return "image_extract_fields", False
        return "image_describe", False

    if is_document:
        if _matches_action(normalized, DELETE_ACTION_CUES):
            # Wait, DELETE_ACTION_CUES is not imported either. Let's make sure we import all required ACTION_CUES.
            return "document_extract_text", False
        if any(keyword_matches(normalized, cue) for cue in ("phan tich", "phân tích", "analyse", "analyze", "analysis", "xem", "mo ta", "mô tả")):
            return "document_summarize", True
        if any(keyword_matches(normalized, cue) for cue in ("tom tat", "tóm tắt", "summary", "summarize")):
            return "document_summarize", True
        if any(keyword_matches(normalized, cue) for cue in ("hoi", "hỏi", "answer", "question", "tra loi", "trả lời", "tim trong", "tìm trong", "noi gi", "nói gì")):
            return "document_search_answer", True
        if any(keyword_matches(normalized, cue) for cue in ("trich truong", "trích trường", "lay thong tin", "lấy thông tin", "fields", "metadata")):
            return "document_extract_fields", True
        if any(keyword_matches(normalized, cue) for cue in ("doc file", "đọc file", "trich text", "trích text", "extract text", "noi dung", "nội dung")):
            return "document_extract_text", True
        return "document_extract_text", False

    if is_audio:
        if any(keyword_matches(normalized, cue) for cue in ("tom tat", "tóm tắt", "summary", "summarize")):
            return "audio_summarize", True
        if any(keyword_matches(normalized, cue) for cue in ("chep loi", "chép lời", "transcribe", "doi sang text", "đổi sang text", "nghe lai", "nghe lại")):
            return "audio_transcribe", True
        return "audio_transcribe", False

    if is_video:
        if any(keyword_matches(normalized, cue) for cue in ("tom tat", "tóm tắt", "summary", "summarize")):
            return "video_summarize", True
        if any(keyword_matches(normalized, cue) for cue in ("chep loi", "chép lời", "transcribe", "phu de", "phụ đề", "subtitle")):
            return "video_transcribe", True
        return "video_transcribe", False

    return "", False
