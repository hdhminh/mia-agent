import urllib.request
import json
import subprocess

intents = [
    # CHAT intents
    ("xin chào", "chat"), ("chào bạn", "chat"), ("hello", "chat"), ("hi bạn", "chat"),
    ("hey", "chat"), ("ê bạn", "chat"), ("ngủ ngon", "chat"), ("chúc ngủ ngon", "chat"),
    ("tạm biệt", "chat"), ("bye", "chat"), ("khỏe không", "chat"), ("bạn có khỏe không", "chat"),
    ("tâm sự đi", "chat"), ("kể chuyện cho tôi nghe", "chat"), ("bạn tên gì", "chat"),
    ("bạn là ai", "chat"), ("vui quá", "chat"), ("buồn quá", "chat"), ("chán thật", "chat"),
    ("hôm nay thế nào", "chat"), ("chào buổi sáng", "chat"), ("chào buổi tối", "chat"),
    ("haha", "chat"), ("cảm ơn", "chat"), ("thanks", "chat"), ("bạn ơi", "chat"),
    ("oke bạn", "chat"), ("thú vị nhỉ", "chat"), ("hay đó", "chat"), ("đồng ý", "chat"),
    # TOOL intents
    ("giá vàng hôm nay", "tool"), ("giá vàng sjc", "tool"), ("thời tiết hôm nay", "tool"),
    ("thời tiết ngày mai", "tool"), ("đọc báo", "tool"), ("tin tức hôm nay", "tool"),
    ("tìm kiếm thông tin", "tool"), ("tra cứu", "tool"), ("tính toán", "tool"),
    ("tóm tắt bài viết", "tool"), ("dịch thuật", "tool"), ("dịch sang tiếng anh", "tool"),
    ("mở ứng dụng", "tool"), ("chứng khoán", "tool"), ("tỷ giá ngoại tệ", "tool"),
    ("phân tích dữ liệu", "tool"), ("tìm kiếm trên google", "tool"), ("gửi email", "tool"),
    ("đặt lịch nhắc", "tool"), ("tính tiền", "tool"), ("xem lịch", "tool"),
    ("tra từ điển", "tool"), ("tìm bài hát", "tool"), ("xem phim", "tool"),
    ("kiểm tra thông tin", "tool"), ("tìm địa chỉ", "tool"), ("bản đồ", "tool"),
    ("đặt hàng", "tool"), ("order đồ ăn", "tool"), ("tìm nhà hàng", "tool"),
    ("calendar", "tool"), ("google calendar", "tool"), ("lịch hôm nay", "tool"),
    ("lịch ngày mai", "tool"), ("lịch tuần này", "tool"), ("lịch tuần sau", "tool"),
    ("tạo lịch", "tool"), ("đặt lịch", "tool"), ("tạo sự kiện", "tool"),
    ("đặt sự kiện", "tool"), ("xóa lịch", "tool"), ("hủy lịch", "tool"),
    ("kiểm tra lịch rảnh", "tool"), ("kiểm tra lịch bận", "tool"),
    ("meeting hôm nay", "tool"), ("lịch họp", "tool"), ("có rảnh không", "tool"),
    ("tạo lịch họp từ 9h đến 10h", "tool"), ("đặt lịch gặp khách 14h-15h30", "tool"),
    ("tạo sự kiện demo kết thúc lúc 5h chiều", "tool"), ("lịch hôm nay có gì", "tool"),
    ("ngày mai tôi có lịch gì", "tool"), ("xóa lịch họp team chiều mai", "tool"),
    ("hủy sự kiện gặp khách thứ 2", "tool"),
    ("xem mail", "tool"), ("xem email", "tool"), ("gmail", "tool"), ("inbox", "tool"),
    ("hộp thư", "tool"), ("hộp thư đến", "tool"), ("mail mới", "tool"), ("email mới", "tool"),
    ("check mail", "tool"), ("kiểm tra mail", "tool"), ("kiểm tra email", "tool"),
    ("đọc mail", "tool"), ("đọc email", "tool"), ("nội dung mail", "tool"), ("nội dung email", "tool"),
    ("read mail", "tool"), ("read email", "tool"), ("gửi mail", "tool"), ("gửi email", "tool"),
    ("soạn mail", "tool"), ("soạn email", "tool"), ("viết nháp email", "tool"), ("draft email", "tool"),
    ("draft mail", "tool"), ("send mail", "tool"), ("send email", "tool"),
    ("tìm mail", "tool"), ("tìm email", "tool"), ("tìm kiếm mail", "tool"), ("tìm kiếm email", "tool"),
    ("search mail", "tool"), ("search email", "tool"), ("trả lời mail", "tool"), ("trả lời email", "tool"),
    ("reply mail", "tool"), ("reply email", "tool"), ("gửi mail cho sếp nội dung báo cáo", "tool"),
    ("đọc mail từ Google", "tool"), ("tìm mail hóa đơn", "tool"), ("xem mail hôm nay có gì", "tool"),
    ("có mail mới không", "tool"), ("trả lời mail từ khách hàng", "tool"),
    ("gửi nháp", "tool"), ("gửi email nháp", "tool"), ("gửi mail nháp", "tool"),
    ("send draft", "tool"), ("gửi nháp mail test@gmail.com Chào bạn", "tool"),
    ("soạn mail test@gmail.com Chào bạn", "tool"), ("draft email test@gmail.com Chào bạn", "tool"),
    ("google drive", "tool"), ("xem drive", "tool"), ("xem file drive", "tool"), ("file gan day", "tool"),
    ("danh sach file drive", "tool"), ("tim file hop dong", "tool"), ("search file bao cao", "tool"),
    ("thong tin file bao cao", "tool"), ("tao folder Khach hang", "tool"), ("tao thu muc Du an", "tool"),
    ("create folder archive 2025", "tool"), ("tao file ghi chu.txt noi dung Xin chao", "tool"),
    ("tao tep todo.txt noi dung mua sua", "tool"), ("create file note.txt content hello team", "tool"),
    ("upload file nay vao drive", "tool"), ("luu file nay vao drive", "tool"), ("download file bao cao", "tool"),
    ("tai file hop dong", "tool"), ("share file bao cao cho email", "tool"), ("chia se file hop dong", "tool"),
    ("xuat file bao cao sang pdf", "tool"), ("export file sang pdf", "tool"), ("doi ten file A thanh B", "tool"),
    ("di chuyen file A vao folder B", "tool"), ("copy file mau hop dong thanh hop dong khach A", "tool"),
    ("xoa file test", "tool"), ("xoa folder Du an cu", "tool"), ("xoa thu muc Archive 2024", "tool"),
    ("delete folder old reports", "tool"),
    ("google docs", "tool"), ("docs help", "tool"), ("tao doc Project Plan noi dung Muc tieu du an", "tool"),
    ("doc doc Project Plan", "tool"), ("them vao doc Project Plan: hom nay da sua Drive Upload", "tool"),
    ("tim doc Project Plan", "tool"), ("xoa doc Project Plan", "tool"),
    ("google sheets", "tool"), ("sheets help", "tool"), ("tao sheet Chi tieu", "tool"),
    ("doc sheet Chi tieu", "tool"), ("them dong vao sheet Chi tieu: cafe,30000,an uong", "tool"),
    ("cap nhat sheet Chi tieu o B2 thanh 35000", "tool"), ("tim sheet Chi tieu", "tool"),
    ("xoa sheet Chi tieu", "tool"),
    ("rut gon link https://example.com", "tool"),
    ("rut gon link https://example.com trong 7 ngay", "tool"),
    ("short link https://example.com 24h", "tool"),
    ("tao link ngan https://example.com het han sau 30 ngay", "tool"),
    ("tao link ngan https://example.com vinh vien", "tool"),
    ("shortlink help", "tool")
]

def pg_exec(sql):
    subprocess.run(
        ["docker", "exec", "postgres", "psql", "-U", "n8n", "-d", "vectordb", "-c", sql],
        check=False, capture_output=True
    )

def get_embedding(text):
    req = urllib.request.Request(
        "http://localhost:11434/api/embeddings",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["embedding"]

# Setup table
pg_exec("CREATE EXTENSION IF NOT EXISTS vector;")
pg_exec("CREATE TABLE IF NOT EXISTS intents (id serial PRIMARY KEY, content text, metadata jsonb, embedding vector(768));")
pg_exec("TRUNCATE TABLE intents;")

print(f"Ingesting {len(intents)} intent samples into Postgres PGVector...")

for i, (text, intent) in enumerate(intents):
    emb = get_embedding(text)
    emb_str = "[" + ",".join(str(x) for x in emb) + "]"
    
    # Use parameterized-style via psql stdin to avoid escaping hell
    meta = json.dumps({"intent": intent})
    sql = f"INSERT INTO intents (content, metadata, embedding) VALUES (E'{text}', '{meta}'::jsonb, '{emb_str}');"
    subprocess.run(
        ["docker", "exec", "postgres", "psql", "-U", "n8n", "-d", "vectordb", "-c", sql],
        capture_output=True, env={"PGPASSWORD": "n8n_password"}
    )
    print(f"  [{i+1}/{len(intents)}] '{text}' => {intent}")

print("\nDone! Verifying row count...")
subprocess.run(
    ["docker", "exec", "postgres", "psql", "-U", "n8n", "-d", "vectordb", "-c", "SELECT count(*) FROM intents;"],
)
