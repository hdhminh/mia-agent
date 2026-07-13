# Mia Code Agent Setup

Mia dùng OpenCode để làm việc code trong workspace riêng, không còn đi theo hướng sửa file cứng cho từng tác vụ.

## Runtime

- `mia-core` quyết định khi nào một yêu cầu là tác vụ code.
- `mia-opencode` là gateway nội bộ, quản lý workspace và gọi `opencode run`.
- Mọi project Mia tự tạo sẽ nằm trong `/home/huynhminh/Projects/mia-workspaces`.
- n8n vẫn không được mở shell command.

## Environment

Thêm hoặc cập nhật các biến sau trong `.env`:

```env
MIA_CODE_ENABLED=true
MIA_CODE_GATEWAY_URL=http://mia-opencode:8015
MIA_CODE_GATEWAY_TOKEN=replace_with_code_gateway_secret
MIA_CODE_TIMEOUT_SECONDS=180
MIA_CODE_MODEL=openrouter/deepseek/deepseek-v4-flash
MIA_CODE_ALLOWED_ROOTS=/host-projects
MIA_CODE_WORKSPACE_ROOT=/workspaces
MIA_CODE_HOST_WORKSPACE_ROOT=/home/huynhminh/Projects/mia-workspaces
MIA_CODE_ALLOWED_REGISTRIES=pypi.org,files.pythonhosted.org,registry.npmjs.org,github.com,api.github.com,proxy.golang.org,crates.io,index.crates.io
MIA_CODE_ALLOWED_COMMAND_PREFIXES=git status,git diff,git log,git show,git branch,git rev-parse,git ls-files,git grep,python,python3,pytest,ruff,mypy,uv,pip install,pip3 install,npm install,npm run,npm test,pnpm install,pnpm run,pnpm test,yarn install,yarn run,yarn test,node,go,cargo,make
```

Tương thích ngược:

- `MIA_CODE_RUNNER_URL`
- `MIA_CODE_RUNNER_TOKEN`
- `MIA_CODE_RUNNER_TIMEOUT_SECONDS`

Mia vẫn đọc các biến cũ nếu anh chưa đổi hết ngay.

## Workspace Policy

- Project mới: Mia ghi trực tiếp vào workspace riêng dưới `mia-workspaces`.
- Project local sẵn có: Mia phải `import` vào sandbox trước, rồi chỉ `apply` ngược khi anh xác nhận.
- Push branch hoặc tạo PR: luôn cần xác nhận rõ ràng.

## Safety

- OpenCode bị chặn đọc `.env` thực.
- Web fetch và web search bị tắt trong code runtime.
- Bash chỉ được mở cho danh sách prefix đã khai báo.
- Registry cài package được giới hạn bằng danh sách allowlist ở trên.

## Start

```bash
docker compose --env-file /home/huynhminh/Projects/mia-agent/.env -f /home/huynhminh/Projects/mia-agent/infra/docker-compose.yml up -d --build mia-opencode mia-core
```

## Expected Usage

Ví dụ các yêu cầu Mia nên xử lý được:

```text
tạo project mới trong Projects tên landing-demo rồi làm portfolio html css
import repo /host-projects/mia-agent rồi sửa bug phần router
xem diff project code hiện tại
apply thay đổi project code này về repo gốc
push branch cho project code này
```
