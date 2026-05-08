# Google Calendar workflows

## Muc tieu

Tach workflow Calendar thanh nhieu file nho de de import va quan ly trong n8n:

- `workflow_sub_google_calendar_master.json`: sub-master router cho Calendar
- `workflow_sub_google_calendar_create_event.json`
- `workflow_sub_google_calendar_list_today.json`
- `workflow_sub_google_calendar_list_tomorrow.json`
- `workflow_sub_google_calendar_find_event.json`
- `workflow_sub_google_calendar_delete_event.json`
- `workflow_sub_google_calendar_check_availability.json`
- `workflow_sub_google_calendar_help.json`

## Cach dung

1. Import tung workflow con truoc.
2. Import `workflow_sub_google_calendar_master.json` sau cung.
3. Dat bien moi truong `N8N_API_KEY` de master co the lookup workflow id dong qua API.
4. Sau khi test on dinh, moi chuyen tool/chuoi goi workflow chinh sang file master moi.

## Ghi chu

- Master moi khong can gan tay `workflowId` cho tung node con nua.
- Moi workflow con tu gui tin nhan Telegram sau khi xu ly xong.
