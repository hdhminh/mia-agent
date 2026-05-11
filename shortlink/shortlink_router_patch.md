# Short Link Router Patch

Thêm service mới vào AI Advanced / Tool Router để lệnh rút gọn link không bị route nhầm sang Search/Web.

## 1. Thêm workflowMap

```js
const workflowMap = {
  gold:      'Sub-workflow: Giá Vàng',
  news:      'Sub-workflow: Tin Tức',
  search:    'Sub-workflow: Tìm Kiếm Web',
  weather:   'Sub-workflow: Thời Tiết',
  calendar:  'Sub-workflow: Google Calendar Master',
  gmail:     'Sub-workflow: Google Gmail Master',
  drive:     'Sub-workflow: Google Drive Master',
  docs:      'Sub-workflow: Google Docs Master',
  sheets:    'Sub-workflow: Google Sheets Master',
  shortlink: 'Sub-workflow: Short Link Create'
};
```

## 2. Thêm detect

```js
const hasShortlinkCue =
  /\b(shortlink|short link|shorten url|rut gon link|rút gọn link|tao link ngan|tạo link ngắn|thu gon url|thu gọn url|link ngan|link ngắn)\b/.test(text);
```

## 3. Đặt Short Link trước Search/Web

```js
if (hasGoldCue) toolKey = 'gold';
else if (hasNewsCue) toolKey = 'news';
else if (hasWeatherCue) toolKey = 'weather';
else if (hasCalendarCue) toolKey = 'calendar';
else if (hasDriveCue || hasDriveShareWithEmail) toolKey = 'drive';
else if (hasDocsCue) toolKey = 'docs';
else if (hasSheetsCue) toolKey = 'sheets';
else if (hasGmailCue) toolKey = 'gmail';
else if (hasShortlinkCue) toolKey = 'shortlink';
else if (text.includes('tim') || text.includes('search') || text.includes('tra cuu') || text.includes('cho toi biet') || text.includes('thong tin ve') || text.includes('duckduckgo') || text.includes('google')) toolKey = 'search';
```

## 4. Payload phải giữ

Khi route sang sub-workflow, cần giữ nguyên:

- `chatId`
- `rawText`
- `message`
- `payload`
- `toolKey`

Project hiện tại đã giữ phần lớn context này. Chỉ cần chắc rằng patch shortlink không làm rơi `chatId` hoặc `rawText`.

## 5. Tên workflow cần import

Workflow service dùng cho router:

```text
Sub-workflow: Short Link Create
```
