#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / "workflows/core/workflow_mia_tool_gateway.json"

PREPARE_CODE = r"""
const source = $('Webhook Tool Request').item.json || {};
const body = source.body || source;
const headers = source.headers || {};
const expectedToken = String($env.MIA_TOOL_GATEWAY_TOKEN || '').trim();
const providedToken = String(headers['x-mia-tool-token'] || headers['X-Mia-Tool-Token'] || '').trim();

if (expectedToken && providedToken !== expectedToken) {
  return [{ json: { ok: false, error: 'Unauthorized tool gateway token.' } }];
}

const tool = String(body.tool || '').trim();
const args = body.args && typeof body.args === 'object' ? body.args : {};
const requestId = String(body.requestId || '').trim();
const originChatId = String(body.chatId || '').trim();
const deliveryMode = String(body.deliveryMode || 'return').trim() || 'return';
const backendChatId = originChatId;

function clean(value) {
  return String(value || '').trim();
}

const toolConfig = {
  'weather.get': {
    workflowKey: 'weather',
    build: (a) => ({
      text: `thời tiết ${clean(a.location)}`.trim(),
      location: clean(a.location),
    }),
  },
  'gold.get_price': {
    workflowKey: 'gold',
    build: () => ({ text: 'giá vàng hôm nay' }),
  },
  'news.get': {
    workflowKey: 'news',
    build: (a) => ({
      text: clean(a.topic) ? `tin tức ${clean(a.topic)}` : 'tin tức hôm nay',
      topic: clean(a.topic),
    }),
  },
  'search.web': {
    workflowKey: 'search',
    build: (a) => ({
      text: `tìm kiếm ${clean(a.query)}`.trim(),
      query: clean(a.query),
    }),
  },
  'web.read_url': {
    workflowKey: 'web.master',
    build: (a) => {
      const url = clean(a.url || a.link || a.sourceUrl || a.source_url);
      const instruction = clean(a.instruction || a.text || a.prompt) || (url ? `đọc link này ${url}` : 'đọc link này');
      return {
        text: instruction,
        url,
        instruction,
        prompt: instruction,
        maxChars: Number(a.maxChars || a.max_chars || 0) || 0,
      };
    },
  },
  'web.summarize_url': {
    workflowKey: 'web.master',
    build: (a) => {
      const url = clean(a.url || a.link || a.sourceUrl || a.source_url);
      const instruction = clean(a.instruction || a.text || a.prompt) || (url ? `tóm tắt link này ${url}` : 'tóm tắt link này');
      return {
        text: instruction,
        url,
        instruction,
        prompt: instruction,
        maxChars: Number(a.maxChars || a.max_chars || 0) || 0,
      };
    },
  },
  'web.ask_url': {
    workflowKey: 'web.master',
    build: (a) => {
      const url = clean(a.url || a.link || a.sourceUrl || a.source_url);
      const question = clean(a.question || a.instruction || a.text || a.prompt) || (url ? `hỏi tiếp link này ${url}` : 'hỏi tiếp link này');
      return {
        text: question,
        url,
        instruction: question,
        question,
        prompt: question,
        maxChars: Number(a.maxChars || a.max_chars || 0) || 0,
      };
    },
  },

  'calendar.help': {
    workflowKey: 'calendar.help',
    build: () => ({ text: 'calendar help' }),
  },
  'calendar.list_today': {
    workflowKey: 'calendar.list_today',
    build: () => ({ text: 'lịch hôm nay' }),
  },
  'calendar.list_tomorrow': {
    workflowKey: 'calendar.list_tomorrow',
    build: () => ({ text: 'lịch ngày mai' }),
  },
  'calendar.find_event': {
    workflowKey: 'calendar.find_event',
    build: (a) => ({ text: clean(a.instruction) || 'tìm sự kiện lịch' }),
  },
  'calendar.create_event': {
    workflowKey: 'calendar.create_event',
    build: (a) => ({ text: clean(a.instruction) || 'tạo lịch' }),
  },
  'calendar.delete_event': {
    workflowKey: 'calendar.delete_event',
    build: (a) => ({ text: clean(a.instruction) || 'xóa lịch' }),
  },
  'calendar.check_availability': {
    workflowKey: 'calendar.check_availability',
    build: (a) => ({ text: clean(a.instruction) || 'kiểm tra lịch rảnh' }),
  },

  'gmail.help': {
    workflowKey: 'gmail.help',
    build: () => ({ text: 'gmail help' }),
  },
  'gmail.list_inbox': {
    workflowKey: 'gmail.list_inbox',
    build: () => ({ text: 'xem mail' }),
  },
  'gmail.read_email': {
    workflowKey: 'gmail.read_email',
    build: (a) => ({ text: clean(a.instruction) || 'đọc email' }),
  },
  'gmail.search_email': {
    workflowKey: 'gmail.search_email',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm email ${clean(a.query)}` : 'tìm email'),
      query: clean(a.query),
    }),
  },
  'gmail.send_email': {
    workflowKey: 'gmail.send_email',
    build: (a) => ({ text: clean(a.instruction) || 'gửi email' }),
  },
  'gmail.draft_email': {
    workflowKey: 'gmail.draft_email',
    build: (a) => ({ text: clean(a.instruction) || 'soạn email' }),
  },
  'gmail.reply_email': {
    workflowKey: 'gmail.reply_email',
    build: (a) => ({ text: clean(a.instruction) || 'trả lời email' }),
  },

  'github.help': {
    workflowKey: 'github.help',
    build: () => ({ text: 'github help' }),
  },

  'github.list_user_repos': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.username) || 'xem repo cua minh',
      username: clean(a.username),
      visibility: clean(a.visibility),
      limit: Number(a.limit || 20) || 20,
      page: Number(a.page || 1) || 1,
    }),
  },
  'github.search_repos': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.query) || clean(a.topic) || 'tim repo',
      query: clean(a.query),
      topic: clean(a.topic),
      language: clean(a.language),
      sortBy: clean(a.sortBy || a.sort_by),
      limit: Number(a.limit || 10) || 10,
      page: Number(a.page || 1) || 1,
    }),
  },

  'github.get_repo': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.repoUrl) || clean(a.repo) || 'xem repo github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
    }),
  },
  'github.get_repo_tree': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.repoUrl) || clean(a.repo) || 'xem cấu trúc repo github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      path: clean(a.path),
      ref: clean(a.ref),
      limit: Number(a.limit || 20) || 20,
    }),
  },
  'github.list_branches': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.repoUrl) || clean(a.repo) || 'xem branch github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      limit: Number(a.limit || 20) || 20,
    }),
  },
  'github.list_commits': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.repoUrl) || clean(a.repo) || 'xem commit github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      ref: clean(a.ref),
      limit: Number(a.limit || 20) || 20,
    }),
  },
  'github.get_commit': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.repoUrl) || clean(a.repo) || clean(a.ref) || 'xem chi tiet commit github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      ref: clean(a.ref),
    }),
  },
  'github.get_file': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.path) || clean(a.repoUrl) || clean(a.repo) || 'doc file github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      path: clean(a.path),
      ref: clean(a.ref),
      maxChars: Number(a.maxChars || 4000) || 4000,
    }),
  },
  'github.search_code': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.query) || clean(a.repoUrl) || clean(a.repo) || 'tim code github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      query: clean(a.query),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'github.get_diff': {
    workflowKey: 'github.master',
    build: (a) => ({
      text: clean(a.instruction) || clean(a.base) || clean(a.head) || clean(a.repoUrl) || clean(a.repo) || 'xem diff github',
      repo: clean(a.repo),
      owner: clean(a.owner),
      repoName: clean(a.repoName),
      repoUrl: clean(a.repoUrl),
      base: clean(a.base),
      head: clean(a.head),
    }),
  },

  'drive.help': {
    workflowKey: 'drive.help',
    build: () => ({ text: 'drive help' }),
  },
  'drive.list_files': {
    workflowKey: 'drive.list_files',
    build: () => ({ text: 'xem file drive' }),
  },
  'drive.search_file': {
    workflowKey: 'drive.search_file',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm file ${clean(a.query)}` : 'tìm file'),
      query: clean(a.query),
      fileName: clean(a.fileName || a.query),
      mimeType: clean(a.mimeType),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'drive.get_file_info': {
    workflowKey: 'drive.get_file_info',
    build: (a) => ({ text: clean(a.instruction) || 'xem chi tiết file' }),
  },
  'drive.create_folder': {
    workflowKey: 'drive.create_folder',
    build: (a) => ({ text: clean(a.instruction) || 'tạo folder' }),
  },
  'drive.create_file': {
    workflowKey: 'drive.create_file',
    build: (a) => ({ text: clean(a.instruction) || 'tạo file' }),
  },
  'drive.upload_file': {
    workflowKey: 'drive.upload_file',
    build: (a) => ({ text: clean(a.instruction) || 'upload file' }),
  },
  'drive.download_file': {
    workflowKey: 'drive.download_file',
    build: (a) => ({ text: clean(a.instruction) || 'tải file' }),
  },
  'drive.share_file': {
    workflowKey: 'drive.share_file',
    build: (a) => ({ text: clean(a.instruction) || 'share file' }),
  },
  'drive.move_file': {
    workflowKey: 'drive.move_file',
    build: (a) => ({ text: clean(a.instruction) || 'di chuyển file' }),
  },
  'drive.rename_file': {
    workflowKey: 'drive.rename_file',
    build: (a) => ({ text: clean(a.instruction) || 'đổi tên file' }),
  },
  'drive.copy_file': {
    workflowKey: 'drive.copy_file',
    build: (a) => ({ text: clean(a.instruction) || 'copy file' }),
  },
  'drive.delete_file': {
    workflowKey: 'drive.delete_file',
    build: (a) => ({ text: clean(a.instruction) || 'xóa file' }),
  },
  'drive.delete_folder': {
    workflowKey: 'drive.delete_folder',
    build: (a) => ({ text: clean(a.instruction) || 'xóa folder' }),
  },
  'drive.export_file': {
    workflowKey: 'drive.export_file',
    build: (a) => ({ text: clean(a.instruction) || 'export file' }),
  },

  'docs.help': {
    workflowKey: 'docs.help',
    build: () => ({ text: 'docs help' }),
  },
  'docs.search_doc': {
    workflowKey: 'docs.search_doc',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm doc ${clean(a.query)}` : 'tìm doc'),
      query: clean(a.query),
      docName: clean(a.docName || a.query),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'docs.read_doc': {
    workflowKey: 'docs.read_doc',
    build: (a) => ({ text: clean(a.instruction) || 'xem doc' }),
  },
  'docs.create_doc': {
    workflowKey: 'docs.create_doc',
    build: (a) => ({ text: clean(a.instruction) || 'tạo doc' }),
  },
  'docs.append_doc': {
    workflowKey: 'docs.append_doc',
    build: (a) => ({ text: clean(a.instruction) || 'thêm vào doc' }),
  },
  'docs.delete_doc': {
    workflowKey: 'docs.delete_doc',
    build: (a) => ({ text: clean(a.instruction) || 'xóa doc' }),
  },

  'sheets.help': {
    workflowKey: 'sheets.help',
    build: () => ({ text: 'sheets help' }),
  },
  'sheets.search_sheet': {
    workflowKey: 'sheets.search_sheet',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm sheet ${clean(a.query)}` : 'tìm sheet'),
      query: clean(a.query),
      sheetName: clean(a.sheetName || a.query),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'sheets.read_sheet': {
    workflowKey: 'sheets.read_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'xem sheet' }),
  },
  'sheets.create_sheet': {
    workflowKey: 'sheets.create_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'tạo sheet' }),
  },
  'sheets.append_row': {
    workflowKey: 'sheets.append_row',
    build: (a) => ({ text: clean(a.instruction) || 'thêm dòng vào sheet' }),
  },
  'sheets.update_cell': {
    workflowKey: 'sheets.update_cell',
    build: (a) => ({ text: clean(a.instruction) || 'cập nhật sheet' }),
  },
  'sheets.delete_sheet': {
    workflowKey: 'sheets.delete_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'xóa sheet' }),
  },

  'shortlink.create': {
    workflowKey: 'shortlink.create',
    build: (a) => {
      const url = clean(a.url);
      const ttl = clean(a.ttl);
      return {
        text: ttl ? `rút gọn link ${url} ${ttl}` : `rút gọn link ${url}`,
        url,
        ttl,
      };
    },
  },

  'calendar.assistant': {
    workflowKey: 'calendar.master',
    build: (a) => ({ text: clean(a.instruction) || 'calendar help' }),
  },
  'gmail.assistant': {
    workflowKey: 'gmail.master',
    build: (a) => ({ text: clean(a.instruction) || 'gmail help' }),
  },
  'drive.assistant': {
    workflowKey: 'drive.master',
    build: (a) => ({ text: clean(a.instruction) || 'drive help' }),
  },
  'docs.assistant': {
    workflowKey: 'docs.master',
    build: (a) => ({ text: clean(a.instruction) || 'docs help' }),
  },
  'sheets.assistant': {
    workflowKey: 'sheets.master',
    build: (a) => ({ text: clean(a.instruction) || 'sheets help' }),
  },
};

if (!tool) {
  return [{ json: { ok: false, error: 'Missing tool name.' } }];
}

const config = toolConfig[tool];
if (!config) {
  return [{ json: { ok: false, error: `Unsupported or invalid tool request: ${tool}` } }];
}

const built = config.build(args || {});
const text = clean(built.text);
if (!text) {
  return [{ json: { ok: false, error: `Unsupported or invalid tool request: ${tool}` } }];
}

return [{
  json: {
    ok: true,
    tool,
    workflowKey: config.workflowKey,
    text,
    rawText: text,
    chatId: backendChatId,
    originChatId,
    requestId,
    deliveryMode,
    args,
    payload: { tool, args, requestId, originChatId, deliveryMode },
    message: { text, caption: text },
    ...built,
  }
}];
""".strip()

ROUTE_CODE = r"""
const source = $('Prepare Tool Request').item.json || $json || {};
const workflowMap = {
  weather: 'm1ip8fFcTkdBwtWh',
  gold: 'KRRETdOwKih9MNPh',
  news: 'dX9MXm49hdVAproP',
  search: '72gE9VPYxBgxFn6h',

  'calendar.help': 'buFXNQy3jqWDmpqe',
  'calendar.list_today': 'fbbeN6ckzosQJv14',
  'calendar.list_tomorrow': 'mwuGFWvzZ47770HO',
  'calendar.find_event': 'R5yJqwK9Y8hVGzcQ',
  'calendar.create_event': 'lQUROmYRGrPOfGru',
  'calendar.delete_event': 'zTyOoljgq4XoXUnZ',
  'calendar.check_availability': 'QNGbJJxdxx5bkYRS',
  'calendar.master': 'hEGn8N6rE17tMw5T',

  'gmail.help': 'efiXM0nYtf8h5oN1',
  'gmail.list_inbox': 'bUttIwvNK8gokFRY',
  'gmail.read_email': 'KMSgPWsLgD78Lgqs',
  'gmail.search_email': 'AsyVChldV5uHWMLv',
  'gmail.send_email': 'bsMiSbmWuz04ED7d',
  'gmail.draft_email': '95MhxIrGwcGCzqfJ',
  'gmail.reply_email': '8O7sp8oZjnYp8LPR',
  'gmail.master': 's5LDuZZpOCAYiQsf',

  'github.help': 'EAjktOSsda0CNGcv',
  'github.master': 'SZZSe1XuJx507pwK',

  'drive.help': '248qYlIWrhgkbw5a',
  'drive.list_files': 'ByX1wU72gZyR0dmz',
  'drive.search_file': 'kJ2TJUZESrqF3PSK',
  'drive.get_file_info': 'EtGHnyz7zIUeX7BT',
  'drive.create_folder': 'eZK8FwtV0DEZ2iGw',
  'drive.create_file': '1dCaJf0LLvPvLfEf',
  'drive.upload_file': 'CQ0pTKvmWRsc1EIg',
  'drive.download_file': 'HWdqSk7Ypm050tMj',
  'drive.share_file': '1GZEqdbawBTQ1uGI',
  'drive.move_file': 'Y9eTfqjWgS4OxZLb',
  'drive.rename_file': 'ckwW3SXzyTYZtVUD',
  'drive.copy_file': 'x76DaXdWmvZmqtuj',
  'drive.delete_file': 'Yg27A2SbktcGd3LH',
  'drive.delete_folder': 'fzVMUuApymKD8CRC',
  'drive.export_file': 'bqFzCUZ5pBhpMFaP',
  'drive.master': 'abTxYqrVCN4Qzz5U',

  'docs.help': 'vMfknpP9mURW6wpG',
  'docs.search_doc': '14Xy6V6vrcsLQnaN',
  'docs.read_doc': 'Q2GmORDNyNLKoHjq',
  'docs.create_doc': 'eiKAYFRQ5WODOIsJ',
  'docs.append_doc': 'g224aehzAvc7e6Ey',
  'docs.delete_doc': 'GH0RIzGys3QjYl9f',
  'docs.master': 'kO3D2tjgJmy3CvSg',

  'sheets.help': 'KKM9UszskWpawgUG',
  'sheets.search_sheet': 'FkjdZUfve4hIpE8T',
  'sheets.read_sheet': 'PNiB0UmyVcmICyBh',
  'sheets.create_sheet': 'TqKhGvLdtz6vM4iv',
  'sheets.append_row': 'ZJvMK3osguI9UdyE',
  'sheets.update_cell': 't7WfKIJjuKDYnRnf',
  'sheets.delete_sheet': 'QkFLuoiyQCyhtLbf',
  'sheets.master': '0cwoCCOYhAldS4Qj',

  'shortlink.create': 'D1cdbPhZef9glsNh',
  'web.master': 'y4V9eGjssR8sSJLb',
};

const workflowId = workflowMap[source.workflowKey || ''];
if (!workflowId) {
  return [{ json: { ok: false, error: `Unsupported workflow key: ${source.workflowKey || '(empty)'}`, tool: source.tool || '', workflowKey: source.workflowKey || '', requestId: source.requestId || '' } }];
}
return [{ json: { ...source, workflowId } }];
""".strip()

NORMALIZE_CODE = r"""
const source = $('Prepare Tool Request').item.json || {};
const output = $json || {};

function decodeEntities(value = '') {
  return String(value)
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
}

function htmlToPlainText(value = '') {
  return decodeEntities(String(value || ''))
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li>/gi, '- ')
    .replace(/<\/h\d>/gi, '\n')
    .replace(/<a[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>/gi, '$2: $1')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const raw = String(
  output.text ||
  output.output ||
  output.response ||
  output.responseText ||
  ''
).replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

const text = htmlToPlainText(raw) || raw || JSON.stringify(output);

return [{
  json: {
    ok: true,
    tool: source.tool || '',
    workflowKey: source.workflowKey || '',
    requestId: source.requestId || '',
    text,
    data: output,
  }
}];
""".strip()


def main() -> None:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    for node in workflow.get("nodes", []):
        name = node.get("name")
        if name == "Prepare Tool Request":
            node["parameters"]["jsCode"] = PREPARE_CODE
        elif name == "Route Tool":
            node["parameters"]["jsCode"] = ROUTE_CODE
        elif name == "Normalize Tool Result":
            node["parameters"]["jsCode"] = NORMALIZE_CODE

    WORKFLOW_PATH.write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
