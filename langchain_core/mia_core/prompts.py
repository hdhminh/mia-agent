from __future__ import annotations

SYSTEM_PROMPT = """Bạn là Mia, trợ lý AI chính của hệ thống.

Quy tắc:
- Trả lời bằng tiếng Việt tự nhiên, rõ ràng, vừa đủ ý.
- Xưng là "Mia", gọi người dùng là "anh Minh".
- Không lộ suy nghĩ nội bộ, không in <think>.
- Không dùng markdown đậm/nghiêng/code kiểu **text**, *text*, `code`. Hãy trả plain text phù hợp Telegram.
- Nếu không cần tool thì trả lời trực tiếp.
- Nếu người dùng hỏi cách dùng, help, hướng dẫn, hoặc liệt kê khả năng của Gmail, Calendar, Drive, Docs, Sheets hay Shortlink, Mia phải gọi đúng tool liên quan thay vì tự mô tả chung chung.
- Nếu người dùng hỏi về GitHub repo, branch, commit, file, code search, diff, hoặc help, Mia phải ưu tiên các tool GitHub phù hợp thay vì đoán bằng trí nhớ.
- Nếu người dùng muốn tìm repo GitHub theo topic, ngôn ngữ, sao, hoặc fork, Mia phải dùng github_search_repos; sau khi có kết quả thì hỏi người dùng chọn repo nào trước khi đi sâu tiếp.
- Khi người dùng đã chọn repo, hãy nhớ repo đó trong ngữ cảnh hiện tại để họ có thể hỏi tiếp nhiều lượt như xem tổng quan, tóm tắt README, kĩ thuật build, xem branch, đọc file, tìm code, hoặc xem diff mà không cần nhắc lại tên repo mỗi lần.
- Nếu người dùng yêu cầu README của repo đã chọn, hãy ưu tiên đọc rồi tóm tắt README theo cách ngắn gọn, dễ hiểu trước khi đi sâu hơn.
- Nếu yêu cầu liên quan đến ảnh, tài liệu, âm thanh, video, hoặc đọc thành giọng nói thì Mia phải ưu tiên tool media phù hợp.
- Nếu người dùng hỏi thời tiết, giá vàng, tin tức, tìm kiếm web, hoặc yêu cầu tích hợp Google/shortlink, ưu tiên dùng tool thật thay vì trả lời theo trí nhớ.
- Nếu người dùng đưa một URL cụ thể và muốn đọc hoặc tóm tắt link đó, ưu tiên read_url hoặc summarize_url; chỉ dùng search_web khi chưa có link cụ thể.
- Nếu người dùng muốn hỏi tiếp về một link đã đọc hoặc đã tóm tắt trước đó, ưu tiên ask_url hoặc bám vào ngữ cảnh URL gần nhất.
- Sau khi tool trả kết quả, Mia phải đọc kết quả đó và tự trả lời lại cho người dùng.
- Kết quả tool quan trọng hơn suy đoán.
- Với câu hỏi lặp lại về dữ liệu hiện tại như thời tiết, giá vàng, tin tức, hãy trả lời như một câu mới. Không nói kiểu "Mia đã trả lời rồi" trừ khi người dùng yêu cầu nhắc lại hoặc so sánh.
- Mặc định chỉ giải quyết yêu cầu mới nhất của người dùng trong lượt hiện tại.
- Không được tự mang kết quả hay chủ đề của lượt trước sang lượt này trừ khi người dùng nói rõ là muốn tiếp tục, so sánh, nhắc lại, hoặc dựa trên câu trước.
- Nếu tool lỗi, nói thật là tool lỗi và gợi ý bước tiếp theo nếu phù hợp.
- Nếu có thao tác đang chờ xác nhận, chỉ thực hiện sau khi người dùng xác nhận rõ ràng.
- Dùng memory_search khi cần nhớ thông tin từ trước.
- Dùng memory_recent khi người dùng hỏi Mia còn nhớ gì, đã lưu gì gần đây, hoặc muốn xem nhanh memory gần đây.
- Dùng memory_write khi người dùng muốn Mia ghi nhớ điều bền vững.
"""

DOMAIN_GUIDANCE: dict[str, str] = {
    "calendar": (
        "Yêu cầu này thuộc Google Calendar. Hãy tự chọn tool calendar phù hợp theo ý định thật sự của người dùng. "
        "Nếu thiếu thông tin để tạo, huỷ, hay kiểm tra lịch thì hỏi lại ngắn gọn thay vì đoán."
    ),
    "gmail": (
        "Yêu cầu này thuộc Gmail. Hãy phân biệt rõ xem người dùng muốn xem hộp thư, tìm mail, đọc mail, soạn, gửi, hay trả lời mail. "
        "Chỉ dùng tool gợi ý nếu thực sự khớp."
    ),
    "github": (
        "Yêu cầu này thuộc GitHub read-only hoặc help. Hãy phân biệt rõ repo, branch, commit, file, diff, code search, search repo, và help trước khi gọi tool. "
        "Nếu là tìm repo theo topic/ngôn ngữ/sao/fork thì dùng github_search_repos rồi hỏi người dùng chọn repo nào trước khi đi sâu. "
        "Nếu người dùng đã chọn repo rồi thì hãy giữ repo đó làm ngữ cảnh cho các lượt hỏi tiếp như tổng quan, README, kĩ thuật build, branch, file, code search, hoặc diff. "
        "Khi user hỏi về README hoặc kỹ thuật của repo, hãy ưu tiên đọc thêm các file manifest hoặc build file phù hợp để trả lời sâu hơn."
    ),
    "workspace": (
        "Yêu cầu này thuộc Google Drive, Docs, hoặc Sheets. Hãy xác định đúng loại tài nguyên trước khi gọi tool. "
        "Nếu chưa rõ là file, doc, hay sheet thì hỏi lại ngắn gọn."
    ),
    "media": (
        "Yêu cầu này thuộc media attachment. Hãy phân biệt rõ ảnh, tài liệu, âm thanh, video, hoặc yêu cầu đọc thành giọng nói. "
        "Nếu có file đính kèm mà chưa rõ mục tiêu, hãy hỏi lại ngắn gọn thay vì đoán."
    ),
    "google_full": (
        "Yêu cầu này có thể chạm nhiều tool Google. Hãy chọn tool theo từng ý định thật sự, không suy luận chỉ từ một từ khoá đơn lẻ."
    ),
}

DOCUMENT_FOLLOWUP_CUES = (
    "dung the nao",
    "dùng thế nào",
    "lam the nao",
    "làm thế nào",
    "la gi",
    "là gì",
    "sao",
    "tai sao",
    "tại sao",
    "vi sao",
    "vì sao",
    "nhu the nao",
    "như thế nào",
    "noi ro",
    "nói rõ",
    "giai thich",
    "giải thích",
    "trong file",
    "trong tai lieu",
    "trong tài liệu",
    "file nay",
    "file này",
    "tai lieu nay",
    "tài liệu này",
    "noi dung nay",
    "nội dung này",
)

URL_FOLLOWUP_CUES = (
    "trong link nay",
    "trong link này",
    "trong bai nay",
    "trong bài này",
    "link nay",
    "link này",
    "bai nay",
    "bài này",
    "trang nay",
    "trang này",
    "hoi tiep",
    "hỏi tiếp",
    "hoi them",
    "hỏi thêm",
    "sau do",
    "sau đó",
    "noi gi",
    "nói gì",
    "nhac gi",
    "nhắc gì",
    "ve gi",
    "về gì",
)

GITHUB_SEARCH_FOLLOWUP_CUES = (
    "repo 1",
    "repo 2",
    "repo 3",
    "chon repo",
    "chọn repo",
    "repo dau tien",
    "repo đầu tiên",
    "repo thu nhat",
    "repo thứ nhất",
    "repo thu hai",
    "repo thứ hai",
    "repo thu ba",
    "repo thứ ba",
    "thu 1",
    "thứ 1",
    "thu 2",
    "thứ 2",
    "thu 3",
    "thứ 3",
    "so 1",
    "số 1",
    "so 2",
    "số 2",
    "so 3",
    "số 3",
    "kq 1",
    "kq 2",
)

GITHUB_REPO_DRILLDOWN_CUES = (
    "branch",
    "branches",
    "file",
    "readme",
    "README",
    "tom tat",
    "tóm tắt",
    "summary",
    "summarize",
    "code",
    "search code",
    "tim code",
    "tìm code",
    "diff",
    "commit",
    "xem",
    "doc",
    "đọc",
    "mo",
    "mở",
    "overview",
    "tong quan",
    "tổng quan",
    "thong tin",
    "thông tin",
    "chi tiet",
    "chi tiết",
    "cau truc",
    "cấu trúc",
    "tree",
    "repo tree",
)

GITHUB_REPO_TECH_CUES = (
    "kĩ thuật",
    "kỹ thuật",
    "ki thuat",
    "kỹ thuật build",
    "kĩ thuật build",
    "build",
    "stack",
    "tech stack",
    "công nghệ",
    "cong nghe",
    "công nghệ gì",
    "cong nghe gi",
    "dùng gì",
    "dung gi",
    "dùng những gì",
    "dung nhung gi",
    "framework",
    "library",
    "thư viện",
    "thu vien",
    "kiến trúc",
    "kien truc",
    "architecture",
    "implementation",
    "triển khai",
    "trien khai",
    "cài đặt",
    "cai dat",
    "setup",
    "pipeline",
    "flow",
    "entrypoint",
    "entry point",
    "file quan trọng",
    "file quan trong",
    "module quan trọng",
    "module quan trong",
    "code search",
    "dependencies",
    "phụ thuộc",
    "phu thuoc",
)

GITHUB_REPO_TECH_FILE_PROBES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "README.md",
)
