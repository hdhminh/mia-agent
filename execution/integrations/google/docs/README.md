# Google Docs Domain

## Kiến trúc hiện tại

Mia hiện gọi Docs theo action-level capability thay vì để `Docs Master` parse lại câu lệnh.

Action chính:

- `docs.help`
- `docs.search_doc`
- `docs.read_doc`
- `docs.create_doc`
- `docs.append_doc`
- `docs.delete_doc`

## File trong domain

- `workflow_sub_google_docs_help.json`
- `workflow_sub_google_docs_search_doc.json`
- `workflow_sub_google_docs_read_doc.json`
- `workflow_sub_google_docs_create_doc.json`
- `workflow_sub_google_docs_append_doc.json`
- `workflow_sub_google_docs_delete_doc.json`
- `workflow_sub_google_docs_master.json`

## Vai trò của `master`

`workflow_sub_google_docs_master.json` là lớp tương thích cũ:

- có thể dùng cho workflow n8n còn gửi text tự nhiên vào Docs
- không còn là đường mặc định của Mia

## Lệnh mẫu

- `docs help`
- `tìm doc project`
- `xem doc Project Proposal`
- `tạo doc Test Mia nội dung xin chào`
- `thêm vào doc Project Plan: cập nhật mới`
- `xóa doc Test Mia`

## Ghi chú

- `docs.search_doc` hiện là action rất quan trọng vì Mia có thể trả thẳng danh sách tài liệu + link.
- Delete trong domain này là đưa tài liệu vào trash, không xóa vĩnh viễn.
