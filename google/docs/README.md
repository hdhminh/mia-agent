# Google Docs workflows

## Muc tieu

Tach Google Docs thanh service rieng de xu ly noi dung tai lieu:

- `workflow_sub_google_docs_master.json`
- `workflow_sub_google_docs_help.json`
- `workflow_sub_google_docs_create_doc.json`
- `workflow_sub_google_docs_read_doc.json`
- `workflow_sub_google_docs_append_doc.json`
- `workflow_sub_google_docs_search_doc.json`
- `workflow_sub_google_docs_delete_doc.json`

## Cach dung

1. Import tung sub-workflow truoc.
2. Import `workflow_sub_google_docs_master.json` sau cung.
3. Dat `N8N_API_KEY` de master lookup workflow id dong.
4. Dung chung credential Google Drive OAuth2 de goi Drive API va Docs API.

## Lenh ho tro

- `docs help`
- `tao doc Project Plan noi dung Muc tieu du an`
- `doc doc Project Plan`
- `them vao doc Project Plan: Cap nhat moi`
- `tim doc Project Plan`
- `xoa doc Project Plan`

## Ghi chu

- Service nay chi tap trung vao noi dung Google Docs.
- Export PDF/DOCX/TXT van dung flow Drive Export.
- Delete chi dua tai lieu vao thung rac, khong xoa vinh vien.
