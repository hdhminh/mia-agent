# Short Link Test Cases

## Telegram

1. `rút gọn link https://example.com`
2. `rút gọn link https://example.com trong 7 ngày`
3. `short link https://example.com 24h`
4. `tạo link ngắn https://example.com vĩnh viễn`
5. `shortlink help`
6. URL có `&` trong query không làm lỗi Telegram HTML

## Validation

7. Thiếu URL
8. `javascript:alert(1)`
9. `ftp://example.com`
10. `http://localhost:5678` khi `SHORTLINK_ALLOW_LOCAL=false`
11. TTL vượt max bị clamp và bot báo rõ

## Redirect

12. `GET https://go.huynhminh.com/<id>` hợp lệ
13. ID không tồn tại trả `404`
14. ID hết hạn trả `410`
15. `clicks` tăng sau mỗi redirect

## Integration

16. Router không route nhầm sang Search/Web
17. Global Error Monitor được gắn cho workflow mới
18. Postgres migration chạy OK

## Lệnh test gợi ý

```bash
curl -i "https://n8n.huynhminh.com/webhook/shortlink/go?id=<id>"
curl -i "https://go.huynhminh.com/<id>"
```

## Cách tạo link để test redirect

- Cách 1: route từ Telegram qua `Sub-workflow: Short Link Create`
- Cách 2: trong n8n, mở workflow `Sub-workflow: Short Link Create` và chạy manual execution với payload có:
  - `chatId`
  - `rawText`
  - hoặc `text`
  - hoặc `message.text`
  - hoặc `message.caption`
  - hoặc `payload.text`
