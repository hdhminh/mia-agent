# Google Gmail workflows

## Muc tieu

Tach workflow Gmail thanh nhieu file nho de de import va quan ly trong n8n:

- `workflow_sub_google_gmail_master.json`: sub-master router cho Gmail
- `workflow_sub_google_gmail_list_inbox.json`: xem email moi nhat
- `workflow_sub_google_gmail_read_email.json`: doc chi tiet email
- `workflow_sub_google_gmail_send_email.json`: gui email moi
- `workflow_sub_google_gmail_search_email.json`: tim kiem email
- `workflow_sub_google_gmail_reply_email.json`: tra loi email
- `workflow_sub_google_gmail_help.json`: huong dan su dung

## Cach dung

1. Import tung workflow con truoc.
2. Import `workflow_sub_google_gmail_master.json` sau cung.
3. Dat bien moi truong `N8N_API_KEY` de master co the lookup workflow id dong qua API.
4. Cau hinh Gmail OAuth2 credential trong n8n.

## Cac lenh ho tro

- `xem mail` / `hộp thư` / `inbox` - Xem email mới nhất
- `đọc mail ...` / `nội dung mail ...` - Đọc chi tiết email
- `gửi mail ...` / `soạn mail ...` - Gửi email mới
- `tìm mail ...` / `search mail ...` - Tìm kiếm email
- `trả lời mail ...` / `reply mail ...` - Trả lời email
- `gmail help` - Hướng dẫn sử dụng

## Ghi chu

- Master moi khong can gan tay `workflowId` cho tung node con nua.
- Moi workflow con tu gui tin nhan Telegram sau khi xu ly xong.
