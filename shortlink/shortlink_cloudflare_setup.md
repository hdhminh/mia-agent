# Short Link Cloudflare Setup

Mục tiêu public URL:

```text
https://go.huynhminh.com/<id>
```

Backend n8n:

```text
https://n8n.huynhminh.com/webhook/shortlink/go?id=<id>
```

## Phương án A

Thêm Public Hostname trực tiếp vào Cloudflare Tunnel:

1. Mở Zero Trust Tunnel đang dùng cho `n8n.huynhminh.com`.
2. Thêm Public Hostname:
   - Subdomain: `go`
   - Domain: `huynhminh.com`
   - Service: `http://n8n:5678`
3. Nếu bạn có thể rewrite path ở upstream hoặc Cloudflare rules để `/abc12345` thành `/webhook/shortlink/go?id=abc12345` thì dùng được.

Vì n8n webhook backend hiện dùng path cố định `/webhook/shortlink/go?id=<id>`, phương án A thường vẫn cần một lớp rewrite.

## Phương án B - Khuyến nghị

Dùng Cloudflare Worker để map:

```text
https://go.huynhminh.com/<id>
```

thành:

```text
https://n8n.huynhminh.com/webhook/shortlink/go?id=<id>
```

### Bước 1. Tạo DNS/subdomain

- Tạo hostname `go.huynhminh.com`
- Trỏ route này cho Worker hoặc dùng Worker Route trực tiếp

### Bước 2. Tạo Worker

- Tạo Worker mới
- Dán nội dung từ file [cloudflare_worker_shortlink.js](/home/huynhminh/Projects/n8n/cloudflare_worker_shortlink.js)

### Bước 3. Gắn route

Gắn route:

```text
go.huynhminh.com/*
```

### Bước 4. Set backend URL

Worker mặc định gọi:

```text
https://n8n.huynhminh.com/webhook/shortlink/go
```

Nếu muốn chỉnh linh hoạt, dùng biến môi trường Worker `SHORTLINK_BACKEND_URL`.

### Bước 5. Test

```bash
curl -i "https://n8n.huynhminh.com/webhook/shortlink/go?id=test1234"
curl -i "https://go.huynhminh.com/test1234"
```

## Lưu ý

- Worker chỉ rewrite path/id sang backend, không giữ secret.
- Worker reject ID rỗng hoặc format bất thường.
- Nên dùng `redirect: 'manual'` để giữ nguyên response của backend.
- Public URL trả cho Telegram luôn phải là `https://go.huynhminh.com/<id>`, không đưa URL webhook dài ra ngoài.
