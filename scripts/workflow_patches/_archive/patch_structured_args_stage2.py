#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def replace_or_fail(code: str, old: str, new: str, *, label: str) -> str:
    if old not in code:
        raise ValueError(f"missing pattern for {label}: {old[:80]!r}")
    return code.replace(old, new, 1)


def patch_node(path: Path, node_name: str, transform) -> None:
    workflow = json.loads(path.read_text())
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            code = node["parameters"]["jsCode"]
            node["parameters"]["jsCode"] = transform(code)
            path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
            print(f"patched {path.name}:{node_name}")
            return
    raise ValueError(f"node {node_name!r} not found in {path}")


def patch_docs_read(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="docs_read args",
    )
    code = replace_or_fail(
        code,
        "const docId = source.docId || source.fileId || source.targetId || source.payload?.docId || '';",
        "const docId = source.docId || source.documentId || source.fileId || source.targetId || args.docId || args.documentId || args.fileId || source.payload?.docId || '';",
        label="docs_read docId",
    )
    code = replace_or_fail(
        code,
        "const docName = cleanName(source.docName || source.fileName || source.title || body);",
        "const docName = cleanName(source.docName || source.fileName || source.title || args.docName || args.fileName || args.title || body);",
        label="docs_read docName",
    )
    return code


def patch_docs_create(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="docs_create args",
    )
    code = replace_or_fail(
        code,
        "let title = cleanName(source.title || source.docTitle || source.fileName || source.documentTitle || '');",
        "let title = cleanName(source.title || source.docTitle || source.fileName || source.documentTitle || args.title || args.docTitle || args.fileName || '');",
        label="docs_create title",
    )
    code = replace_or_fail(
        code,
        "let content = source.content || source.docContent || '';",
        "let content = source.content || source.docContent || args.content || args.docContent || '';",
        label="docs_create content",
    )
    code = replace_or_fail(
        code,
        "    title,\n    content: String(content || ''),",
        "    title,\n    content: String(content || ''),\n    folderId: String(source.folderId || args.folderId || '').trim(),",
        label="docs_create return folderId",
    )
    return code


def patch_docs_append(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="docs_append args",
    )
    code = replace_or_fail(
        code,
        "let docId = source.docId || source.fileId || source.targetId || '';",
        "let docId = source.docId || source.documentId || source.fileId || source.targetId || args.docId || args.documentId || args.fileId || '';",
        label="docs_append docId",
    )
    code = replace_or_fail(
        code,
        "let docName = cleanName(source.docName || source.fileName || '');",
        "let docName = cleanName(source.docName || source.fileName || args.docName || args.fileName || '');",
        label="docs_append docName",
    )
    code = replace_or_fail(
        code,
        "let content = String(source.content || '').trim();",
        "let content = String(source.content || args.content || '').trim();",
        label="docs_append content",
    )
    return code


def patch_docs_delete(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="docs_delete args",
    )
    code = replace_or_fail(
        code,
        "const docId = source.docId || source.fileId || source.targetId || '';",
        "const docId = source.docId || source.documentId || source.fileId || source.targetId || args.docId || args.documentId || args.fileId || '';",
        label="docs_delete docId",
    )
    code = replace_or_fail(
        code,
        "const docName = cleanName(source.docName || source.fileName || body);",
        "const docName = cleanName(source.docName || source.fileName || args.docName || args.fileName || body);",
        label="docs_delete docName",
    )
    return code


def patch_sheets_read(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="sheets_read args",
    )
    code = replace_or_fail(
        code,
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  payload.spreadsheetId ||\n  payload.sheetId ||\n  payload.fileId ||\n  '';",
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  args.spreadsheetId ||\n  args.sheetId ||\n  args.fileId ||\n  payload.spreadsheetId ||\n  payload.sheetId ||\n  payload.fileId ||\n  '';",
        label="sheets_read spreadsheetId",
    )
    code = replace_or_fail(
        code,
        "  source.range ||\n  payload.range ||\n  parseRange(raw) ||\n  'A1:Z30';",
        "  source.range ||\n  args.range ||\n  payload.range ||\n  parseRange(raw) ||\n  'A1:Z30';",
        label="sheets_read range",
    )
    code = replace_or_fail(
        code,
        "  source.sheetTab ||\n  payload.sheetTab ||\n  parseSheetTab(raw) ||\n  '';",
        "  source.sheetTab ||\n  args.sheetTab ||\n  payload.sheetTab ||\n  parseSheetTab(raw) ||\n  '';",
        label="sheets_read sheetTab",
    )
    code = replace_or_fail(
        code,
        "  source.sheetName ||\n  source.title ||\n  source.query ||\n  payload.sheetName ||\n  payload.title ||\n  payload.query ||\n  parseSheetName(raw)\n);",
        "  source.sheetName ||\n  source.title ||\n  source.query ||\n  args.sheetName ||\n  args.title ||\n  args.query ||\n  payload.sheetName ||\n  payload.title ||\n  payload.query ||\n  parseSheetName(raw)\n);",
        label="sheets_read sheetName",
    )
    return code


def patch_sheets_create(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="sheets_create args",
    )
    code = replace_or_fail(
        code,
        "const title = cleanName(source.title || source.sheetTitle || source.fileName || body);",
        "const title = cleanName(source.title || source.sheetTitle || source.fileName || args.title || args.sheetTitle || args.sheetName || body);",
        label="sheets_create title",
    )
    return code


def patch_sheets_append(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="sheets_append args",
    )
    code = replace_or_fail(
        code,
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  source.targetId ||\n  ctx.payload.spreadsheetId ||\n  ctx.payload.sheetId ||\n  ctx.payload.fileId ||\n  '';",
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  source.targetId ||\n  args.spreadsheetId ||\n  args.sheetId ||\n  args.fileId ||\n  ctx.payload.spreadsheetId ||\n  ctx.payload.sheetId ||\n  ctx.payload.fileId ||\n  '';",
        label="sheets_append spreadsheetId",
    )
    code = replace_or_fail(
        code,
        "  source.sheetTab ||\n  ctx.payload.sheetTab ||\n  parsed.sheetTab ||\n  '';",
        "  source.sheetTab ||\n  args.sheetTab ||\n  ctx.payload.sheetTab ||\n  parsed.sheetTab ||\n  '';",
        label="sheets_append sheetTab",
    )
    code = replace_or_fail(
        code,
        "  source.sheetName ||\n  source.fileName ||\n  source.title ||\n  source.query ||\n  ctx.payload.sheetName ||\n  ctx.payload.fileName ||\n  ctx.payload.title ||\n  ctx.payload.query ||\n  parsed.sheetName ||\n  ''\n);",
        "  source.sheetName ||\n  source.fileName ||\n  source.title ||\n  source.query ||\n  args.sheetName ||\n  args.fileName ||\n  args.title ||\n  args.query ||\n  ctx.payload.sheetName ||\n  ctx.payload.fileName ||\n  ctx.payload.title ||\n  ctx.payload.query ||\n  parsed.sheetName ||\n  ''\n);",
        label="sheets_append sheetName",
    )
    code = replace_or_fail(
        code,
        "  source.rowData ||\n  source.content ||\n  ctx.payload.rowData ||\n  ctx.payload.content ||\n  parsed.rowData ||\n  ''\n).trim();",
        "  source.rowData ||\n  source.content ||\n  args.rowData ||\n  args.content ||\n  ctx.payload.rowData ||\n  ctx.payload.content ||\n  parsed.rowData ||\n  ''\n).trim();",
        label="sheets_append rowData",
    )
    code = replace_or_fail(
        code,
        "const values = Array.isArray(source.values)\n  ? source.values\n  : parseCsvLine(rowData);",
        "const values = Array.isArray(source.values)\n  ? source.values\n  : Array.isArray(args.values)\n    ? args.values\n    : parseCsvLine(rowData);",
        label="sheets_append values",
    )
    return code


def patch_sheets_update(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="sheets_update args",
    )
    code = replace_or_fail(
        code,
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  source.targetId ||\n  ctx.payload.spreadsheetId ||\n  ctx.payload.sheetId ||\n  ctx.payload.fileId ||\n  '';",
        "  source.spreadsheetId ||\n  source.sheetId ||\n  source.fileId ||\n  source.targetId ||\n  args.spreadsheetId ||\n  args.sheetId ||\n  args.fileId ||\n  ctx.payload.spreadsheetId ||\n  ctx.payload.sheetId ||\n  ctx.payload.fileId ||\n  '';",
        label="sheets_update spreadsheetId",
    )
    code = replace_or_fail(
        code,
        "  source.sheetName ||\n  source.fileName ||\n  source.title ||\n  source.query ||\n  ctx.payload.sheetName ||\n  ctx.payload.fileName ||\n  ctx.payload.title ||\n  ctx.payload.query ||\n  ''\n);",
        "  source.sheetName ||\n  source.fileName ||\n  source.title ||\n  source.query ||\n  args.sheetName ||\n  args.fileName ||\n  args.title ||\n  args.query ||\n  ctx.payload.sheetName ||\n  ctx.payload.fileName ||\n  ctx.payload.title ||\n  ctx.payload.query ||\n  ''\n);",
        label="sheets_update sheetName",
    )
    code = replace_or_fail(
        code,
        "  source.sheetTab ||\n  ctx.payload.sheetTab ||\n  parseSheetTab(raw) ||\n  '';",
        "  source.sheetTab ||\n  args.sheetTab ||\n  ctx.payload.sheetTab ||\n  parseSheetTab(raw) ||\n  '';",
        label="sheets_update sheetTab",
    )
    code = replace_or_fail(
        code,
        "  source.cell ||\n  source.range ||\n  ctx.payload.cell ||\n  ctx.payload.range ||\n  ''\n).trim().toUpperCase();",
        "  source.cell ||\n  source.range ||\n  args.cell ||\n  args.range ||\n  ctx.payload.cell ||\n  ctx.payload.range ||\n  ''\n).trim().toUpperCase();",
        label="sheets_update cell",
    )
    code = replace_or_fail(
        code,
        "  source.value ||\n  ctx.payload.value ||\n  ''\n).trim();",
        "  source.value ||\n  args.value ||\n  ctx.payload.value ||\n  ''\n).trim();",
        label="sheets_update value",
    )
    return code


def patch_sheets_delete(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst ctx = getTelegramContext(source);",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst ctx = getTelegramContext(source);",
        label="sheets_delete args",
    )
    code = replace_or_fail(
        code,
        "const spreadsheetId = source.spreadsheetId || source.sheetId || source.fileId || source.targetId || '';",
        "const spreadsheetId = source.spreadsheetId || source.sheetId || source.fileId || source.targetId || args.spreadsheetId || args.sheetId || args.fileId || '';",
        label="sheets_delete spreadsheetId",
    )
    code = replace_or_fail(
        code,
        "const sheetName = cleanName(source.sheetName || source.fileName || body);",
        "const sheetName = cleanName(source.sheetName || source.fileName || args.sheetName || args.fileName || body);",
        label="sheets_delete sheetName",
    )
    return code


def patch_drive_info(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="drive_info args",
    )
    code = replace_or_fail(
        code,
        "  source.fileId ||\n  source.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        "  source.fileId ||\n  source.targetId ||\n  args.fileId ||\n  args.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        label="drive_info fileId",
    )
    code = replace_or_fail(
        code,
        "  source.fileName ||\n  source.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  extractFileName(raw)\n);",
        "  source.fileName ||\n  source.targetName ||\n  args.fileName ||\n  args.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  extractFileName(raw)\n);",
        label="drive_info fileName",
    )
    return code


def patch_drive_create_folder(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};\nconst args = source.args || payload.args || {};",
        label="drive_create_folder args",
    )
    code = replace_or_fail(
        code,
        "const folderName = String(source.folderName || payload.folderName || raw.replace(/^(tao folder|tao thu muc|create folder)\\s*/i, '')).trim();",
        "const folderName = String(source.folderName || source.name || args.folderName || args.name || payload.folderName || raw.replace(/^(tao folder|tao thu muc|create folder)\\s*/i, '')).trim();",
        label="drive_create_folder name",
    )
    code = replace_or_fail(
        code,
        "const folderId = source.folderId || payload.folderId || 'root';",
        "const folderId = source.folderId || source.parentId || args.folderId || args.parentId || payload.folderId || 'root';",
        label="drive_create_folder folderId",
    )
    return code


def patch_drive_delete_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};\nconst args = source.args || payload.args || {};",
        label="drive_delete_file args",
    )
    code = replace_or_fail(
        code,
        "const fileId = source.fileId || payload.fileId || '';",
        "const fileId = source.fileId || args.fileId || payload.fileId || '';",
        label="drive_delete_file fileId",
    )
    code = replace_or_fail(
        code,
        "const fileName = String(source.fileName || payload.fileName || raw.replace(/^(xoa file|delete file|bo file vao thung rac|move file to trash)\\s*/i, '')).trim();",
        "const fileName = String(source.fileName || args.fileName || payload.fileName || raw.replace(/^(xoa file|delete file|bo file vao thung rac|move file to trash)\\s*/i, '')).trim();",
        label="drive_delete_file fileName",
    )
    return code


def patch_drive_share_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};\nconst args = source.args || payload.args || {};",
        label="drive_share_file args",
    )
    code = replace_or_fail(
        code,
        "const fileId = source.fileId || payload.fileId || '';",
        "const fileId = source.fileId || args.fileId || payload.fileId || '';",
        label="drive_share_file fileId",
    )
    code = replace_or_fail(
        code,
        "const email = source.email || payload.email || (emailMatch ? emailMatch[0] : '');",
        "const email = source.email || args.email || payload.email || (emailMatch ? emailMatch[0] : '');",
        label="drive_share_file email",
    )
    code = replace_or_fail(
        code,
        "const role = source.role || payload.role || 'reader';",
        "const role = source.role || args.role || payload.role || 'reader';",
        label="drive_share_file role",
    )
    code = replace_or_fail(
        code,
        "const fileName = String(source.fileName || payload.fileName || cleaned).trim();",
        "const fileName = String(source.fileName || args.fileName || payload.fileName || cleaned).trim();",
        label="drive_share_file fileName",
    )
    return code


def main() -> None:
    patch_node(ROOT / "google/docs/workflow_sub_google_docs_read_doc.json", "Prepare Action", patch_docs_read)
    patch_node(ROOT / "google/docs/workflow_sub_google_docs_create_doc.json", "Prepare Action", patch_docs_create)
    patch_node(ROOT / "google/docs/workflow_sub_google_docs_append_doc.json", "Prepare Action", patch_docs_append)
    patch_node(ROOT / "google/docs/workflow_sub_google_docs_delete_doc.json", "Prepare Action", patch_docs_delete)

    patch_node(ROOT / "google/sheets/workflow_sub_google_sheets_read_sheet.json", "Prepare Action", patch_sheets_read)
    patch_node(ROOT / "google/sheets/workflow_sub_google_sheets_create_sheet.json", "Prepare Action", patch_sheets_create)
    patch_node(ROOT / "google/sheets/workflow_sub_google_sheets_append_row.json", "Prepare Action", patch_sheets_append)
    patch_node(ROOT / "google/sheets/workflow_sub_google_sheets_update_cell.json", "Prepare Action", patch_sheets_update)
    patch_node(ROOT / "google/sheets/workflow_sub_google_sheets_delete_sheet.json", "Prepare Action", patch_sheets_delete)

    patch_node(ROOT / "google/drive/workflow_sub_google_drive_get_file_info.json", "Prepare Action", patch_drive_info)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_create_folder.json", "Prepare Action", patch_drive_create_folder)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_delete_file.json", "Prepare Action", patch_drive_delete_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_share_file.json", "Prepare Action", patch_drive_share_file)


if __name__ == "__main__":
    main()
