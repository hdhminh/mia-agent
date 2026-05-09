const http = require('http');
const execSync = require('child_process').execSync;

const intents = {
    "xin chào": "chat",
    "chào bạn": "chat",
    "hello": "chat",
    "hi": "chat",
    "ngủ ngon": "chat",
    "khỏe không": "chat",
    "tâm sự đi": "chat",
    "kể chuyện": "chat",
    "vui quá": "chat",
    "buồn quá": "chat",
    "chào buổi sáng": "chat",
    "giá vàng": "tool",
    "thời tiết": "tool",
    "đọc báo": "tool",
    "tin tức": "tool",
    "tìm kiếm": "tool",
    "tra cứu": "tool",
    "tính toán": "tool",
    "tóm tắt": "tool",
    "dịch thuật": "tool",
    "xem lịch": "tool",
    "calendar": "tool",
    "google calendar": "tool",
    "lịch hôm nay": "tool",
    "lịch ngày mai": "tool",
    "lịch tuần này": "tool",
    "lịch tuần sau": "tool",
    "tạo lịch": "tool",
    "đặt lịch": "tool",
    "tạo sự kiện": "tool",
    "đặt sự kiện": "tool",
    "xóa lịch": "tool",
    "hủy lịch": "tool",
    "kiểm tra lịch rảnh": "tool",
    "kiểm tra lịch bận": "tool",
    "lịch họp": "tool",
    "meeting hôm nay": "tool",
    "có rảnh không": "tool",
    "tạo lịch họp từ 9h đến 10h": "tool",
    "đặt lịch gặp khách 14h-15h30": "tool",
    "tạo sự kiện demo kết thúc lúc 5h chiều": "tool",
    "lịch hôm nay có gì": "tool",
    "ngày mai tôi có lịch gì": "tool",
    "xóa lịch họp team chiều mai": "tool",
    "hủy sự kiện gặp khách thứ 2": "tool",
    "xem mail": "tool",
    "xem email": "tool",
    "gmail": "tool",
    "inbox": "tool",
    "hộp thư": "tool",
    "hộp thư đến": "tool",
    "mail mới": "tool",
    "email mới": "tool",
    "check mail": "tool",
    "kiểm tra mail": "tool",
    "kiểm tra email": "tool",
    "đọc mail": "tool",
    "đọc email": "tool",
    "nội dung mail": "tool",
    "nội dung email": "tool",
    "read mail": "tool",
    "read email": "tool",
    "gửi mail": "tool",
    "gửi email": "tool",
    "soạn mail": "tool",
    "soạn email": "tool",
    "viết nháp email": "tool",
    "draft email": "tool",
    "draft mail": "tool",
    "send mail": "tool",
    "send email": "tool",
    "tìm mail": "tool",
    "tìm email": "tool",
    "tìm kiếm mail": "tool",
    "tìm kiếm email": "tool",
    "search mail": "tool",
    "search email": "tool",
    "trả lời mail": "tool",
    "trả lời email": "tool",
    "reply mail": "tool",
    "reply email": "tool",
    "gửi mail cho sếp nội dung báo cáo": "tool",
    "đọc mail từ Google": "tool",
    "tìm mail hóa đơn": "tool",
    "xem mail hôm nay có gì": "tool",
    "có mail mới không": "tool",
    "trả lời mail từ khách hàng": "tool",
    "gửi nháp": "tool",
    "gửi email nháp": "tool",
    "gửi mail nháp": "tool",
    "send draft": "tool",
    "gửi nháp mail test@gmail.com Chào bạn": "tool",
    "soạn mail test@gmail.com Chào bạn": "tool",
    "draft email test@gmail.com Chào bạn": "tool",
    "google drive": "tool",
    "xem drive": "tool",
    "xem file drive": "tool",
    "file gan day": "tool",
    "danh sach file drive": "tool",
    "tim file hop dong": "tool",
    "search file bao cao": "tool",
    "thong tin file bao cao": "tool",
    "tao folder Khach hang": "tool",
    "tao thu muc Du an": "tool",
    "upload file nay vao drive": "tool",
    "luu file nay vao drive": "tool",
    "download file bao cao": "tool",
    "tai file hop dong": "tool",
    "share file bao cao cho email": "tool",
    "chia se file hop dong": "tool",
    "xuat file bao cao sang pdf": "tool",
    "export file sang pdf": "tool",
    "doi ten file A thanh B": "tool",
    "di chuyen file A vao folder B": "tool",
    "copy file mau hop dong thanh hop dong khach A": "tool",
    "xoa file test": "tool"
};

async function getEmbedding(text) {
    return new Promise((resolve, reject) => {
        const req = http.request('http://ollama:11434/api/embeddings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data).embedding));
        });
        req.write(JSON.stringify({ model: 'nomic-embed-text', prompt: text }));
        req.end();
    });
}

async function run() {
    execSync(`psql -h postgres -U n8n -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"`, { env: { PGPASSWORD: 'n8n_password' }});
    execSync(`psql -h postgres -U n8n -d vectordb -c "CREATE TABLE IF NOT EXISTS intents (id serial PRIMARY KEY, content text, metadata jsonb, embedding vector(768));"`, { env: { PGPASSWORD: 'n8n_password' }});
    execSync(`psql -h postgres -U n8n -d vectordb -c "TRUNCATE TABLE intents;"`, { env: { PGPASSWORD: 'n8n_password' }});

    console.log("Ingesting...");
    for (const [text, intent] of Object.entries(intents)) {
        const emb = await getEmbedding(text);
        const embStr = `[${emb.join(',')}]`;
        const sql = `INSERT INTO intents (content, metadata, embedding) VALUES ('${text}', '{"intent":"${intent}"}', '${embStr}');`;
        execSync(`psql -h postgres -U n8n -d vectordb -c '${sql}'`, { env: { PGPASSWORD: 'n8n_password' }});
    }
    console.log("Done!");
}

run().catch(console.error);
