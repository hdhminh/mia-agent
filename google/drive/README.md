# Google Drive workflows

## Muc tieu

Tach workflow Google Drive thanh nhieu file nho de de import va quan ly trong n8n:

- `workflow_sub_google_drive_master.json`
- `workflow_sub_google_drive_list_files.json`
- `workflow_sub_google_drive_search_file.json`
- `workflow_sub_google_drive_get_file_info.json`
- `workflow_sub_google_drive_create_folder.json`
- `workflow_sub_google_drive_create_file.json`
- `workflow_sub_google_drive_upload_file.json`
- `workflow_sub_google_drive_download_file.json`
- `workflow_sub_google_drive_copy_file.json`
- `workflow_sub_google_drive_rename_file.json`
- `workflow_sub_google_drive_move_file.json`
- `workflow_sub_google_drive_delete_folder.json`
- `workflow_sub_google_drive_delete_file.json`
- `workflow_sub_google_drive_share_file.json`
- `workflow_sub_google_drive_export_file.json`
- `workflow_sub_google_drive_help.json`

## Cach dung

1. Import tung workflow con truoc.
2. Import `workflow_sub_google_drive_master.json` sau cung.
3. Dat bien moi truong `N8N_API_KEY` de master co the lookup workflow id dong qua API.
4. Cau hinh Google Drive OAuth2 credential trong n8n.
5. Sau khi test on dinh, moi chuyen tool/chuoi goi workflow chinh sang file master moi.

## Cac lenh ho tro

- `xem file drive`
- `tim file hop dong`
- `thong tin file bao cao`
- `tao folder Khach hang`
- `tao file ghi-chu.txt noi dung Xin chao`
- `upload file nay vao drive`
- `tai file bao cao`
- `copy file mau hop dong thanh hop dong khach A`
- `doi ten file A thanh B`
- `di chuyen file A vao folder B`
- `share file A cho email@example.com`
- `xuat file A sang pdf`
- `xoa folder Du an cu`
- `xoa file A`

## Ghi chu

- Master moi khong can gan tay workflowId cho tung node con nua.
- Moi workflow con tu gui tin nhan Telegram sau khi xu ly xong.
- Create file mac dinh tao file text, ho tro them noi dung truc tiep trong cau lenh.
- Delete chi dua file vao thung rac, khong xoa vinh vien.
- Delete folder chi dua folder vao thung rac, khong xoa vinh vien.
- Drive phu trach quan ly file/folder, upload/download/export/share/move/rename/delete.
- Google Docs service phu trach noi dung tai lieu Google Docs nhu tao/doc/them noi dung/tim/xoa.
- Google Sheets service phu trach noi dung bang tinh Google Sheets nhu tao/doc/them dong/cap nhat o/tim/xoa.
- Export dung cho Google Docs/Sheets/Slides va van di qua Drive service.
- Download dung cho file thuong nhu PDF, anh, DOCX, ZIP.
