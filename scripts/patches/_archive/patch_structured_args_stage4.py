#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def replace_or_fail(code: str, old: str, new: str, *, label: str) -> str:
    if old not in code:
        raise ValueError(f"missing pattern for {label}: {old[:120]!r}")
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


def patch_gateway_prepare(code: str) -> str:
    replacements = [
        (
            """  'drive.create_file': {\n    workflowKey: 'drive.create_file',\n    build: (a) => ({ text: clean(a.instruction) || 'tạo file', name: clean(a.name), content: clean(a.content), mimeType: clean(a.mimeType), parentId: clean(a.parentId) }),\n  },""",
            """  'drive.create_file': {\n    workflowKey: 'drive.create_file',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.name || a.fileName) ? `tạo file ${clean(a.name || a.fileName)}` : 'tạo file'),\n      name: clean(a.name || a.fileName),\n      fileName: clean(a.fileName || a.name),\n      content: clean(a.content),\n      mimeType: clean(a.mimeType),\n      parentId: clean(a.parentId || a.folderId),\n      folderId: clean(a.folderId || a.parentId),\n    }),\n  },""",
            "gateway drive.create_file",
        ),
        (
            """  'drive.download_file': {\n    workflowKey: 'drive.download_file',\n    build: (a) => ({ text: clean(a.instruction) || 'tải file', fileId: clean(a.fileId) }),\n  },""",
            """  'drive.download_file': {\n    workflowKey: 'drive.download_file',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.fileName || a.targetName) ? `tải file ${clean(a.fileName || a.targetName)}` : 'tải file'),\n      fileId: clean(a.fileId || a.targetId),\n      targetId: clean(a.targetId || a.fileId),\n      fileName: clean(a.fileName || a.targetName),\n      targetName: clean(a.targetName || a.fileName),\n    }),\n  },""",
            "gateway drive.download_file",
        ),
        (
            """  'drive.move_file': {\n    workflowKey: 'drive.move_file',\n    build: (a) => ({ text: clean(a.instruction) || 'di chuyển file', fileId: clean(a.fileId), targetFolderId: clean(a.targetFolderId) }),\n  },""",
            """  'drive.move_file': {\n    workflowKey: 'drive.move_file',\n    build: (a) => ({\n      text: clean(a.instruction) || 'di chuyển file',\n      fileId: clean(a.fileId || a.targetId),\n      targetId: clean(a.targetId || a.fileId),\n      fileName: clean(a.fileName),\n      targetFolderId: clean(a.targetFolderId || a.folderId),\n      folderId: clean(a.folderId || a.targetFolderId),\n      targetFolderName: clean(a.targetFolderName || a.folderName),\n      folderName: clean(a.folderName || a.targetFolderName),\n    }),\n  },""",
            "gateway drive.move_file",
        ),
        (
            """  'drive.rename_file': {\n    workflowKey: 'drive.rename_file',\n    build: (a) => ({ text: clean(a.instruction) || 'đổi tên file', fileId: clean(a.fileId), newName: clean(a.newName) }),\n  },""",
            """  'drive.rename_file': {\n    workflowKey: 'drive.rename_file',\n    build: (a) => ({\n      text: clean(a.instruction) || 'đổi tên file',\n      fileId: clean(a.fileId || a.targetId),\n      targetId: clean(a.targetId || a.fileId),\n      fileName: clean(a.fileName || a.targetName),\n      targetName: clean(a.targetName || a.fileName),\n      newName: clean(a.newName),\n    }),\n  },""",
            "gateway drive.rename_file",
        ),
        (
            """  'drive.copy_file': {\n    workflowKey: 'drive.copy_file',\n    build: (a) => ({ text: clean(a.instruction) || 'copy file', fileId: clean(a.fileId), newName: clean(a.newName), parentId: clean(a.parentId) }),\n  },""",
            """  'drive.copy_file': {\n    workflowKey: 'drive.copy_file',\n    build: (a) => ({\n      text: clean(a.instruction) || 'copy file',\n      fileId: clean(a.fileId),\n      fileName: clean(a.fileName),\n      newName: clean(a.newName),\n      parentId: clean(a.parentId || a.targetFolderId),\n      targetFolderId: clean(a.targetFolderId || a.parentId),\n    }),\n  },""",
            "gateway drive.copy_file",
        ),
        (
            """  'drive.delete_folder': {\n    workflowKey: 'drive.delete_folder',\n    build: (a) => ({ text: clean(a.instruction) || 'xóa folder', folderId: clean(a.folderId) }),\n  },""",
            """  'drive.delete_folder': {\n    workflowKey: 'drive.delete_folder',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.folderName || a.targetName) ? `xóa folder ${clean(a.folderName || a.targetName)}` : 'xóa folder'),\n      folderId: clean(a.folderId || a.targetId),\n      targetId: clean(a.targetId || a.folderId),\n      folderName: clean(a.folderName || a.targetName),\n      targetName: clean(a.targetName || a.folderName),\n    }),\n  },""",
            "gateway drive.delete_folder",
        ),
        (
            """  'drive.export_file': {\n    workflowKey: 'drive.export_file',\n    build: (a) => ({ text: clean(a.instruction) || 'export file', fileId: clean(a.fileId), mimeType: clean(a.mimeType) }),\n  },""",
            """  'drive.export_file': {\n    workflowKey: 'drive.export_file',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.fileName || a.targetName) ? `export file ${clean(a.fileName || a.targetName)}` : 'export file'),\n      fileId: clean(a.fileId || a.targetId),\n      targetId: clean(a.targetId || a.fileId),\n      fileName: clean(a.fileName || a.targetName),\n      targetName: clean(a.targetName || a.fileName),\n      mimeType: clean(a.mimeType || a.format),\n      format: clean(a.format || a.mimeType),\n    }),\n  },""",
            "gateway drive.export_file",
        ),
    ]
    for old, new, label in replacements:
        code = replace_or_fail(code, old, new, label=label)
    return code


def patch_create_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="create_file args",
    )
    code = replace_or_fail(
        code,
        "  source.rawText ||\n  source.text ||\n  message.text ||\n  payload.text ||\n  ''",
        "  source.rawText ||\n  source.text ||\n  source.fileName ||\n  args.fileName ||\n  args.name ||\n  message.text ||\n  payload.text ||\n  ''",
        label="create_file raw",
    )
    code = replace_or_fail(
        code,
        "  source.folderId ||\n  payload.folderId ||\n  'root';",
        "  source.folderId ||\n  source.parentId ||\n  args.folderId ||\n  args.parentId ||\n  payload.folderId ||\n  'root';",
        label="create_file folderId",
    )
    code = replace_or_fail(
        code,
        "  source.fileName ||\n  payload.fileName ||\n  parsed.fileName",
        "  source.fileName ||\n  source.name ||\n  args.fileName ||\n  args.name ||\n  payload.fileName ||\n  parsed.fileName",
        label="create_file fileName",
    )
    code = replace_or_fail(
        code,
        "  source.content ??\n  payload.content ??\n  parsed.content;",
        "  source.content ??\n  args.content ??\n  payload.content ??\n  parsed.content;",
        label="create_file content",
    )
    code = replace_or_fail(
        code,
        "  source.mimeType ||\n  payload.mimeType ||\n  '';",
        "  source.mimeType ||\n  args.mimeType ||\n  payload.mimeType ||\n  '';",
        label="create_file mimeType",
    )
    return code


def patch_download_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="download_file args",
    )
    code = replace_or_fail(
        code,
        "  source.rawText ||\n  source.text ||\n  message.text ||\n  payload.text ||\n  ''",
        "  source.rawText ||\n  source.text ||\n  source.fileName ||\n  args.fileName ||\n  args.targetName ||\n  message.text ||\n  payload.text ||\n  ''",
        label="download_file raw",
    )
    code = replace_or_fail(
        code,
        "  source.fileId ||\n  source.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        "  source.fileId ||\n  source.targetId ||\n  args.fileId ||\n  args.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        label="download_file fileId",
    )
    code = replace_or_fail(
        code,
        "  source.fileName ||\n  source.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  extractFileName(raw)",
        "  source.fileName ||\n  source.targetName ||\n  args.fileName ||\n  args.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  extractFileName(raw)",
        label="download_file fileName",
    )
    return code


def patch_move_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="move_file args",
    )
    code = replace_or_fail(
        code,
        "  source.rawText ||\n  source.text ||\n  message.text ||\n  payload.text ||\n  ''",
        "  source.rawText ||\n  source.text ||\n  source.fileName ||\n  args.fileName ||\n  message.text ||\n  payload.text ||\n  ''",
        label="move_file raw",
    )
    code = replace_or_fail(
        code,
        "  source.fileId ||\n  source.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        "  source.fileId ||\n  source.targetId ||\n  args.fileId ||\n  args.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        label="move_file fileId",
    )
    code = replace_or_fail(
        code,
        "  source.targetFolderId ||\n  source.folderId ||\n  payload.targetFolderId ||\n  payload.folderId ||\n  '';",
        "  source.targetFolderId ||\n  source.folderId ||\n  args.targetFolderId ||\n  args.folderId ||\n  payload.targetFolderId ||\n  payload.folderId ||\n  '';",
        label="move_file folderId",
    )
    code = replace_or_fail(
        code,
        "  source.fileName ||\n  payload.fileName ||\n  parsed.fileName",
        "  source.fileName ||\n  args.fileName ||\n  payload.fileName ||\n  parsed.fileName",
        label="move_file fileName",
    )
    code = replace_or_fail(
        code,
        "  source.targetFolderName ||\n  source.folderName ||\n  payload.targetFolderName ||\n  payload.folderName ||\n  parsed.targetFolderName",
        "  source.targetFolderName ||\n  source.folderName ||\n  args.targetFolderName ||\n  args.folderName ||\n  payload.targetFolderName ||\n  payload.folderName ||\n  parsed.targetFolderName",
        label="move_file targetFolderName",
    )
    return code


def patch_rename_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="rename_file args",
    )
    code = replace_or_fail(
        code,
        "  source.rawText ||\n  source.text ||\n  message.text ||\n  payload.text ||\n  ''",
        "  source.rawText ||\n  source.text ||\n  source.fileName ||\n  args.fileName ||\n  message.text ||\n  payload.text ||\n  ''",
        label="rename_file raw",
    )
    code = replace_or_fail(
        code,
        "  source.fileId ||\n  source.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        "  source.fileId ||\n  source.targetId ||\n  args.fileId ||\n  args.targetId ||\n  payload.fileId ||\n  payload.targetId ||\n  '';",
        label="rename_file fileId",
    )
    code = replace_or_fail(
        code,
        "  source.fileName ||\n  source.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  parsed.fileName",
        "  source.fileName ||\n  source.targetName ||\n  args.fileName ||\n  args.targetName ||\n  payload.fileName ||\n  payload.targetName ||\n  parsed.fileName",
        label="rename_file fileName",
    )
    code = replace_or_fail(
        code,
        "  source.newName ||\n  payload.newName ||\n  parsed.newName",
        "  source.newName ||\n  args.newName ||\n  payload.newName ||\n  parsed.newName",
        label="rename_file newName",
    )
    return code


def patch_copy_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="copy_file args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || source.fileName || args.fileName || message.text || payload.text || '').trim();",
        label="copy_file raw",
    )
    code = replace_or_fail(
        code,
        "const fileId = source.fileId || payload.fileId || '';",
        "const fileId = source.fileId || args.fileId || payload.fileId || '';",
        label="copy_file fileId",
    )
    code = replace_or_fail(
        code,
        "let fileName = String(source.fileName || payload.fileName || '').trim();",
        "let fileName = String(source.fileName || args.fileName || payload.fileName || '').trim();",
        label="copy_file fileName",
    )
    code = replace_or_fail(
        code,
        "let newName = String(source.newName || payload.newName || '').trim();",
        "let newName = String(source.newName || args.newName || payload.newName || '').trim();",
        label="copy_file newName",
    )
    code = replace_or_fail(
        code,
        "const targetFolderId = source.targetFolderId || payload.targetFolderId || '';",
        "const targetFolderId = source.targetFolderId || source.parentId || args.targetFolderId || args.parentId || payload.targetFolderId || '';",
        label="copy_file targetFolderId",
    )
    return code


def patch_delete_folder(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\n\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\n\nconst payload = source.payload || {};",
        label="delete_folder args",
    )
    code = replace_or_fail(
        code,
        "  source.rawText ||\n  source.text ||\n  message.text ||\n  payload.text ||\n  ''",
        "  source.rawText ||\n  source.text ||\n  source.folderName ||\n  args.folderName ||\n  args.targetName ||\n  message.text ||\n  payload.text ||\n  ''",
        label="delete_folder raw",
    )
    code = replace_or_fail(
        code,
        "  source.folderId ||\n  source.targetId ||\n  payload.folderId ||\n  payload.targetId ||\n  '';",
        "  source.folderId ||\n  source.targetId ||\n  args.folderId ||\n  args.targetId ||\n  payload.folderId ||\n  payload.targetId ||\n  '';",
        label="delete_folder folderId",
    )
    code = replace_or_fail(
        code,
        "  source.folderName ||\n  source.targetName ||\n  payload.folderName ||\n  payload.targetName ||\n  extractFolderName(raw)",
        "  source.folderName ||\n  source.targetName ||\n  args.folderName ||\n  args.targetName ||\n  payload.folderName ||\n  payload.targetName ||\n  extractFolderName(raw)",
        label="delete_folder folderName",
    )
    return code


def patch_export_file(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="export_file args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || source.text || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || source.fileName || args.fileName || message.text || payload.text || '').trim();",
        label="export_file raw",
    )
    code = replace_or_fail(
        code,
        "const fileId = source.fileId || source.targetId || payload.fileId || payload.targetId || '';",
        "const fileId = source.fileId || source.targetId || args.fileId || args.targetId || payload.fileId || payload.targetId || '';",
        label="export_file fileId",
    )
    code = replace_or_fail(
        code,
        "const fileName = cleanName(source.fileName || source.targetName || payload.fileName || payload.targetName || parsed.fileName);",
        "const fileName = cleanName(source.fileName || source.targetName || args.fileName || args.targetName || payload.fileName || payload.targetName || parsed.fileName);",
        label="export_file fileName",
    )
    code = replace_or_fail(
        code,
        "const requestedFormat = cleanName(source.format || payload.format || parsed.format || '').toLowerCase().replace(/^\\./, '');",
        "const requestedFormat = cleanName(source.format || source.mimeType || args.format || args.mimeType || payload.format || parsed.format || '').toLowerCase().replace(/^\\./, '');",
        label="export_file format",
    )
    return code


def main() -> None:
    patch_node(ROOT / "workflows/core/workflow_mia_tool_gateway.json", "Prepare Tool Request", patch_gateway_prepare)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_create_file.json", "Prepare Action", patch_create_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_download_file.json", "Prepare Action", patch_download_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_move_file.json", "Prepare Action", patch_move_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_rename_file.json", "Prepare Action", patch_rename_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_copy_file.json", "Prepare Action", patch_copy_file)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_delete_folder.json", "Prepare Action", patch_delete_folder)
    patch_node(ROOT / "google/drive/workflow_sub_google_drive_export_file.json", "Prepare Action", patch_export_file)


if __name__ == "__main__":
    main()
