# Shortlink Domain

## Vai trò

`shortlink` là mini-domain tạo và tra cứu link ngắn cho Mia và các workflow khác.

## Action hiện có

- `workflow_shortlink_create.json`
- `workflow_shortlink_redirect.json`

## Kiến trúc hiện tại

- `create` là action backend chính cho Mia.
- `redirect` là action public-facing để chuyển hướng người dùng cuối.
- Worker Cloudflare nằm ở `cloudflare_worker_shortlink.js`.

## Contract

`workflow_shortlink_create.json`

- input:
  - `args.url` hoặc text tự nhiên có URL
  - `args.ttl` tùy chọn
  - `chatId` tùy chọn
  - `deliveryMode` = `return` hoặc `telegram`
- output:
  - `text`
  - `result.id`
  - `result.short_url`
  - `result.long_url`
  - `result.expires_at`

`workflow_shortlink_redirect.json`

- input:
  - path short id từ public route
- output:
  - redirect 301/302
  - hoặc lỗi nếu link hết hạn/không tồn tại

## Ghi chú

- Mia hiện gọi shortlink qua tool `shortlink_create`.
- Domain này đã gần đạt action-level sạch; nếu cần mở rộng tiếp có thể thêm:
  - `workflow_shortlink_info.json`
  - `workflow_shortlink_delete.json`
