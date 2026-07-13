from __future__ import annotations

from agent.i18n import t

DOMAIN_GUIDANCE: dict[str, str] = {
    "calendar": t("domain_guidance.calendar"),
    "gmail": t("domain_guidance.gmail"),
    "github": t("domain_guidance.github"),
    "maps": t("domain_guidance.maps"),
    "smarthome": t("domain_guidance.smarthome"),
    "code": (
        "Yêu cầu này thuộc code agent. Hãy dùng tool code_* để thao tác thật với workspace. "
        "Không trả lời help chung hoặc liệt kê khả năng khi người dùng đã yêu cầu tạo, sửa, đọc, chạy test, xem diff, apply local, hoặc publish code. "
        "Nếu người dùng muốn tạo project mới trong Projects, hãy dùng code_create_project. "
        "Nếu người dùng muốn làm trên project local sẵn có, hãy dùng code_import_existing_project trước. "
        "Sau khi có project thì dùng code_work_on_project cho các lượt tiếp theo. "
        "Nếu người dùng không nói project_id mà hiện chỉ có một project code đang tồn tại, có thể tiếp tục luôn project đó. "
        "Nếu người dùng cho phép apply local rõ ràng thì gọi code_apply_to_existing_project với confirmed=true; nếu chưa cho phép thì chỉ trả diff. "
        "Nếu người dùng cho phép push hoặc tạo PR rõ ràng thì gọi code_publish_project với confirmed=true."
    ),
    "workspace": t("domain_guidance.workspace"),
    "media": t("domain_guidance.media"),
    "google_full": t("domain_guidance.google_full"),
}
