# Memory Domain

## Vai trò

`memory` là domain ghi nhớ dài hạn của Mia.

Đường chạy chính hiện tại:

- `langchain_core/mia_core/memory.py`: repository chính cho Mia core
- `memory/embedder/app.py`: service tạo embedding
- `memory/schema_memory.sql`: schema chuẩn cho Postgres + pgvector

Workflow n8n trong thư mục này là lớp phụ trợ/ops, dùng khi cần:

- debug thủ công trong n8n
- chạy workflow độc lập
- tái sử dụng từ workflow khác ngoài Mia core

## Action hiện có

- `workflow_memory_search.json`
- `workflow_memory_write.json`
- `workflow_memory_recent.json`

## Contract gợi ý

Input chung:

- `chatId`
- `requestId` tùy chọn

`memory_search`

- input:
  - `query`
  - `memory_type` hoặc `memoryType` tùy chọn
  - `limit` tùy chọn
  - `threshold` tùy chọn
- output:
  - `text`
  - `result.items[]`

`memory_write`

- input:
  - `content`
  - `memory_type`
  - `title`
  - `tags`
  - `importance`
- output:
  - `text`
  - `result`

`memory_recent`

- input:
  - `limit`
- output:
  - `text`
  - `result.items[]`

## Ghi chú

- Mia core đang dùng Python repository trực tiếp cho `memory_search`, `memory_recent`, `memory_write`.
- Nếu cần chuẩn hóa thêm, có thể tách riêng workflow setup schema thay vì chạy DDL trong request path.
