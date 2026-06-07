# GitHub Manual Test Prompts

Use these prompts in order to verify the GitHub flow:

## 1) Search repos

| Prompt | Expected behavior |
|---|---|
| `hãy tìm kiếm các repo về video translation nhiều sao nhất trên github` | Route to `github_search_repos` and show a numbered repo list. |
| `tìm repo theo topic paddleocr` | Route to `github_search_repos` with topic search. |
| `tìm repo theo topic ai bằng python sort most stars` | Route to `github_search_repos` with `language=python` and `sortBy=most_stars`. |
| `xem repo của mình trên GitHub` | Route to `github_list_user_repos`. |

## 2) Pick a repo

After a search result, reply with one of these:

| Prompt | Expected behavior |
|---|---|
| `repo 1` | Mia confirms the selected repo and asks what to inspect next. |
| `repo 2` | Mia confirms the selected repo and asks what to inspect next. |
| `chọn repo đầu tiên` | Mia confirms the selected repo and asks what to inspect next. |

## 3) Drill down into the selected repo

After you pick a repo, try these follow-ups:

| Prompt | Expected behavior |
|---|---|
| `xem branch` | Route to `github_list_branches` using the selected repo context. |
| `xem commit gần đây` | Route to `github_list_commits` using the selected repo context. |
| `đọc file README` | Route to `github_get_file` using the selected repo context. |
| `tìm code Session` | Route to `github_search_code` using the selected repo context. |
| `xem diff master...main` | Route to `github_get_diff` using the selected repo context. |

## 4) Direct repo drill-down

| Prompt | Expected behavior |
|---|---|
| `xem repo octocat/Hello-World` | Route to `github_get_repo`. |
| `xem branch octocat/Hello-World` | Route to `github_list_branches`. |
| `doc file README trong repo octocat/Hello-World` | Route to `github_get_file`. |
