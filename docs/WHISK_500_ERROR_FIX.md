# Whisk API 500 Error Fix / Sửa Lỗi 500 Whisk API

## Problem / Vấn Đề

When using Whisk image generation, you may encounter 500 Internal Server errors:

Khi sử dụng tạo ảnh Whisk, bạn có thể gặp lỗi 500 Internal Server:

```
[ERROR] Whisk recipe failed with status 500
[DEBUG] Response: {
  "error": {
    "code": 500,
    "message": "Internal error encountered.",
    "status": "INTERNAL"
  }
}
[WARN] Whisk: Image generation returned no data
[ERROR] Whisk returned no data
```

## Root Cause / Nguyên Nhân

HTTP 500 errors are **transient server-side errors** from Google's Whisk API. They often occur when:

Lỗi HTTP 500 là **lỗi tạm thời từ phía server** của Google Whisk API. Chúng thường xảy ra khi:

1. The API server is temporarily overloaded / Server API tạm thời quá tải
2. Internal service issues / Vấn đề dịch vụ nội bộ
3. Rate limiting or quota issues / Vấn đề giới hạn tốc độ hoặc quota

These errors are usually temporary and can succeed if retried.

Các lỗi này thường tạm thời và có thể thành công nếu thử lại.

## Solution / Giải Pháp

The code has been updated with **automatic retry logic**:

Code đã được cập nhật với **logic tự động thử lại**:

### Features / Tính Năng

1. **Automatic Retry with Exponential Backoff**
   
   **Tự Động Thử Lại với Exponential Backoff**
   
   - Default: 3 retry attempts / Mặc định: 3 lần thử lại
   - Delays: 2s, 4s between retries / Độ trễ: 2s, 4s giữa các lần thử
   - Configurable parameters / Tham số có thể cấu hình

2. **Enhanced Error Parsing**
   
   **Phân Tích Lỗi Nâng Cao**
   
   - Extracts error code, status, and message from JSON response
   - Trích xuất mã lỗi, trạng thái và thông báo từ JSON response
   - Shows detailed error information in logs
   - Hiển thị thông tin lỗi chi tiết trong logs

3. **Smart Retry Logic**
   
   **Logic Thử Lại Thông Minh**
   
   - Only retries 5xx server errors (500-599)
   - Chỉ thử lại lỗi server 5xx (500-599)
   - Doesn't retry client errors (4xx)
   - Không thử lại lỗi client (4xx)
   - Handles network timeouts
   - Xử lý timeout mạng

### Example Log Output / Ví Dụ Output Log

**Before Fix / Trước Khi Sửa:**
```
[ERROR] Whisk recipe failed with status 500
[DEBUG] Response: {"error": {"code": 500...
[ERROR] Whisk returned no data
```

**After Fix / Sau Khi Sửa:**
```
[INFO] Whisk: Running image recipe...
[ERROR] Whisk recipe failed with status 500 (transient error)
[DEBUG] Error details: Code: 500, Status: INTERNAL, Message: Internal error encountered.
[RETRY] Attempt 2/3 after 2.0s delay...
[ERROR] Whisk recipe failed with status 500 (transient error)
[DEBUG] Error details: Code: 500, Status: INTERNAL, Message: Internal error encountered.
[RETRY] Attempt 3/3 after 4.0s delay...
[ERROR] Whisk recipe failed with status 500
[DEBUG] Error details: Code: 500, Status: INTERNAL, Message: Internal error encountered.
[ERROR] All 3 attempts failed. Last error: HTTP 500: Code: 500, Status: INTERNAL, Message: Internal error encountered.
[WARN] Whisk: Image generation returned no data
```

## Configuration / Cấu Hình

The retry behavior can be customized by modifying the function parameters in code:

Hành vi thử lại có thể được tùy chỉnh bằng cách sửa tham số hàm trong code:

```python
# Default behavior
run_image_recipe(
    prompt=prompt,
    recipe_media_inputs=recipe_media_inputs,
    workflow_id=workflow_id,
    session_id=session_id,
    aspect_ratio=aspect_ratio,
    log_callback=log,
    max_retries=3,      # Number of retry attempts
    retry_delay=2.0     # Initial delay in seconds (doubles each retry)
)

# Custom: More retries with longer delays
run_image_recipe(
    prompt=prompt,
    recipe_media_inputs=recipe_media_inputs,
    workflow_id=workflow_id,
    session_id=session_id,
    aspect_ratio=aspect_ratio,
    log_callback=log,
    max_retries=5,      # Try up to 5 times
    retry_delay=3.0     # Start with 3s delay (3s, 6s, 12s, 24s)
)
```

## When to Use / Khi Nào Dùng

### This Fix Helps With / Sửa Lỗi Này Giúp Với

✅ Transient 500 errors / Lỗi 500 tạm thời

✅ Server overload / Quá tải server

✅ Temporary service disruptions / Gián đoạn dịch vụ tạm thời

✅ Network timeout issues / Vấn đề timeout mạng

### This Fix Does NOT Help With / Sửa Lỗi Này KHÔNG Giúp Với

❌ Authentication errors (401) - See WHISK_AUTH_FIX.md

❌ Missing configuration / Thiếu cấu hình

❌ Invalid bearer tokens / Bearer token không hợp lệ

❌ Persistent server failures / Lỗi server liên tục

## Troubleshooting / Xử Lý Sự Cố

### Still Getting 500 After All Retries / Vẫn Gặp 500 Sau Tất Cả Các Lần Thử

If all retry attempts fail, the issue may be:

Nếu tất cả các lần thử đều thất bại, vấn đề có thể là:

1. **Persistent API Outage**
   
   **API Ngừng Hoạt Động Liên Tục**
   
   - Check Google Labs status page
   - Try again later (after 10-30 minutes)
   
   - Kiểm tra trang trạng thái Google Labs
   - Thử lại sau (sau 10-30 phút)

2. **Invalid Bearer Token**
   
   **Bearer Token Không Hợp Lệ**
   
   - Refresh your bearer token (see WHISK_AUTH_FIX.md)
   - Bearer tokens expire after a few hours
   
   - Làm mới bearer token (xem WHISK_AUTH_FIX.md)
   - Bearer token hết hạn sau vài giờ

3. **Quota/Rate Limit Issues**
   
   **Vấn Đề Quota/Giới Hạn Tốc Độ**
   
   - Wait longer between requests
   - Check your API usage limits
   
   - Đợi lâu hơn giữa các request
   - Kiểm tra giới hạn sử dụng API

4. **Request Too Complex**
   
   **Request Quá Phức Tạp**
   
   - Try simpler prompts
   - Use fewer reference images
   - Reduce image sizes
   
   - Thử prompt đơn giản hơn
   - Dùng ít ảnh tham chiếu hơn
   - Giảm kích thước ảnh

### Increase Retry Attempts / Tăng Số Lần Thử

For environments with frequent transient errors:

Cho môi trường với lỗi tạm thời thường xuyên:

1. Modify `services/whisk_service.py`
2. In `generate_image()` function, change the call to:

```python
result_image = run_image_recipe(
    prompt=prompt,
    recipe_media_inputs=recipe_media_inputs,
    workflow_id=workflow_id,
    session_id=session_id,
    aspect_ratio=aspect_ratio,
    log_callback=log,
    max_retries=5,      # Increase from 3 to 5
    retry_delay=3.0     # Increase from 2.0 to 3.0
)
```

## Technical Details / Chi Tiết Kỹ Thuật

### Retry Strategy / Chiến Lược Thử Lại

**Exponential Backoff Algorithm:**

```
Attempt 1: Immediate
Attempt 2: Wait retry_delay * 2^0 = 2.0s
Attempt 3: Wait retry_delay * 2^1 = 4.0s
Attempt 4: Wait retry_delay * 2^2 = 8.0s
...
```

This prevents overwhelming the server while giving it time to recover.

Điều này ngăn chặn làm quá tải server trong khi cho nó thời gian để phục hồi.

### Error Detection / Phát Hiện Lỗi

The code detects retryable errors by:

Code phát hiện lỗi có thể thử lại bằng:

1. Checking HTTP status code: `500 <= status < 600`
2. Parsing JSON error response for details
3. Distinguishing from client errors (4xx) which are not retried

### Code Changes / Thay Đổi Code

**Modified File:** `services/whisk_service.py`

**Function:** `run_image_recipe()`

**Changes:**
- Added `max_retries` parameter (default: 3)
- Added `retry_delay` parameter (default: 2.0)
- Implemented retry loop with exponential backoff
- Enhanced error parsing from JSON responses
- Added detailed logging for each retry attempt
- Better error messages showing parsed error details

---

## Related Documentation / Tài Liệu Liên Quan

- **WHISK_AUTH_FIX.md** - How to fix 401 authentication errors
- **README.md** - General project documentation

---

*Last updated: 2025-11-10*
*Cập nhật lần cuối: 2025-11-10*
