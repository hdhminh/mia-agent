# Google Sheets workflows

## Muc tieu

Tach Google Sheets thanh service rieng de xu ly bang tinh:

- `workflow_sub_google_sheets_master.json`
- `workflow_sub_google_sheets_help.json`
- `workflow_sub_google_sheets_create_sheet.json`
- `workflow_sub_google_sheets_read_sheet.json`
- `workflow_sub_google_sheets_append_row.json`
- `workflow_sub_google_sheets_update_cell.json`
- `workflow_sub_google_sheets_search_sheet.json`
- `workflow_sub_google_sheets_delete_sheet.json`

## Cach dung

1. Import tung sub-workflow truoc.
2. Import `workflow_sub_google_sheets_master.json` sau cung.
3. Dat `N8N_API_KEY` de master lookup workflow id dong.
4. Dung chung credential Google Drive OAuth2 de goi Drive API va Sheets API.

## Lenh ho tro

- `sheets help`
- `tao sheet Chi tieu`
- `doc sheet Chi tieu`
- `them dong vao sheet Chi tieu: cafe,30000,an uong`
- `cap nhat sheet Chi tieu o B2 thanh 35000`
- `tim sheet Chi tieu`
- `xoa sheet Chi tieu`

## Ghi chu

- Service nay tap trung vao noi dung bang tinh Google Sheets.
- Export XLSX/CSV/PDF van dung flow Drive Export.
- Delete chi dua bang tinh vao thung rac, khong xoa vinh vien.
