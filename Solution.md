# Báo Cáo Giải Pháp Codelab (Day 12 - Cloud Infrastructure & Deployment)

Họ và tên: [Điền tên của bạn]  
Thời gian nộp: 12/06/2026

---

## 📍 Part 1: Localhost vs Production

### Exercise 1.1: Danh sách 5 anti-patterns phát hiện trong `develop/app.py`
1. **Hardcoded Secrets:** API key (`sk-hardcoded-fake-key-never-do-this`) và DATABASE_URL bị gán cứng trực tiếp trong code thay vì đọc từ biến môi trường.
2. **Thiếu Config Management:** Chế độ `DEBUG = True` và cấu hình hệ thống `MAX_TOKENS` bị cài đặt cứng trực tiếp trong logic file, không thể thay đổi linh hoạt giữa các môi trường dev/production.
3. **Sử dụng `print` thay vì Structured Logging:** Log thông tin thô bằng `print()` không có timestamp, log level, và vô tình log cả API Key lên terminal.
4. **Không có Health Check Endpoint:** Không cung cấp API `/health` hay `/ready` để cloud orchestrator giám sát trạng thái hoạt động của container.
5. **Cố định Host và Port (Hardcoded Port/Host):** Binding `host="localhost"` và `port=8000` trực tiếp khiến ứng dụng không thể nhận traffic ngoài mạng nội bộ và không nhận diện được Port được cấp động bởi Cloud platforms.

### Exercise 1.3: Bảng so sánh Basic vs Advanced

| Feature | Basic (develop/app.py) | Advanced (production/app.py) | Tại sao quan trọng? |
| :--- | :--- | :--- | :--- |
| **Config** | Hardcode trực tiếp | Đọc từ environment variables thông qua Pydantic Settings | Giúp quản lý cấu hình tập trung, tách biệt code khỏi config theo tiêu chuẩn 12-Factor App. |
| **Health check** | Không có | Cung cấp endpoints `/health` (liveness) và `/ready` (readiness) | Giúp platform tự động khôi phục (self-heal) khi container bị treo và tối ưu routing traffic. |
| **Logging** | `print()` thông thường | Structured JSON logging (sử dụng module logging chuẩn và output JSON) | Giúp thu thập, tìm kiếm và phân tích log tự động dễ dàng trên các log aggregator tập trung. |
| **Shutdown** | Tắt đột ngột (ngắt tiến trình ngay lập tức) | Graceful Shutdown (bắt tín hiệu SIGTERM để dọn dẹp tài nguyên) | Tránh ngắt quãng các request đang xử lý dở dang của người dùng khi tiến hành deploy phiên bản mới. |

### Câu hỏi thảo luận Part 1:
1. **Điều gì xảy ra nếu push code chứa API key hardcode lên GitHub public?**
   - API key sẽ bị các bot quét tự động phát hiện trong vòng vài giây, dẫn đến việc tài khoản bị hack, lạm dụng dịch vụ LLM và phát sinh hóa đơn chi phí khổng lồ.
2. **Tại sao stateless quan trọng khi scale?**
   - Vì khi scale-out (nhiều bản sao ứng dụng chạy song song đằng sau Load Balancer), nếu server có lưu trạng thái (stateful), request tiếp theo của user có thể bị chuyển đến instance khác không có session của họ, gây lỗi ứng dụng. Stateless giúp phân tán request đến bất kỳ instance nào đều xử lý được như nhau.
3. **"dev/prod parity" nghĩa là gì trong thực tế?**
   - Nghĩa là giữ cho môi trường Development, Staging và Production giống nhau nhất có thể về code, dependencies, cấu trúc thư mục, hệ điều hành và services đi kèm (ví dụ: cùng dùng Redis thật thay vì dùng mock in-memory) nhằm giảm thiểu lỗi bất ngờ khi đưa code lên production.

---

## 📍 Part 2: Docker Containerization

### Exercise 2.1: Trả lời câu hỏi Dockerfile cơ bản
1. **Base image là gì?**
   - Base image là `python:3.11`. Đây là ảnh chứa toàn bộ bộ thư viện Python chính thức trên hệ điều hành Debian đầy đủ.
2. **Working directory là gì?**
   - Working directory là `/app`, nơi chứa các file mã nguồn và là thư mục làm việc mặc định trong container.
3. **Tại sao COPY requirements.txt trước?**
   - Để tận dụng cơ chế lưu cache layer của Docker. Khi chỉ thay đổi source code ứng dụng mà không thêm bớt thư viện, Docker sẽ bỏ qua bước cài đặt `pip install` (chạy rất lâu) và dùng luôn cache của layer đó giúp tăng tốc độ build đáng kể.
4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - `ENTRYPOINT` quy định lệnh cố định luôn chạy khi container khởi động (thường là shell chính hoặc executable). `CMD` cung cấp các đối số mặc định cho lệnh đó và có thể dễ dàng bị ghi đè khi ta gõ tham số bổ sung từ CLI khi `docker run`.

### Exercise 2.3: Giải thích Multi-stage build
- **Stage 1 (builder):** Dùng image `python:3.11-slim` để cài đặt các build tool (`gcc`, `libpq-dev`) và tải các thư viện dependencies bằng `pip install --user` vào thư mục `/root/.local`. Stage này chứa nhiều file rác và công cụ biên dịch nặng.
- **Stage 2 (runtime):** Bắt đầu từ một image `python:3.11-slim` sạch hoàn toàn, chỉ copy thư mục dependencies đã cài sẵn `/root/.local` từ builder sang mà không mang theo các build tool rác.
- **Tại sao image nhỏ hơn?** Vì Stage 2 hoàn toàn sạch sẽ, không cài đặt các công cụ biên dịch (`gcc`, `make`...) hay các cache tải xuống, chỉ giữ lại runtime tối thiểu cần thiết để chạy Python app.

### Exercise 2.4: Sơ đồ kiến trúc Docker Compose Stack
```text
┌─────────────────┐
│     Client      │
└────────┬────────┘
         │ (Port 80 hoặc 8000)
         ▼
┌─────────────────┐
│   Nginx (LB)    │
└────────┬────────┘
         │ (Load Balancing)
         ├──────────────────────┬──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Agent Instance 1│    │ Agent Instance 2│    │ Agent Instance 3│
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                ▼
                       ┌─────────────────┐
                       │   Redis Cache   │ (Lưu trữ session history & rate limiting state)
                       └─────────────────┘
```

---

## 📍 Part 3: Cloud Deployment

*Ghi lại kết quả triển khai cloud:*
- **Platform sử dụng:** Railway / Render / GCP Cloud Run
- **Public URL hoạt động:** `http://[url-cua-ban]/health`

---

## 📍 Part 4: API Security

### Exercise 4.3: Trả lời câu hỏi Rate Limiting
1. **Algorithm nào được dùng?**
   - Thuật toán **Sliding Window Log** (hoặc Fixed Window tùy thuộc cấu hình lưu thời gian request trên Redis).
2. **Limit là bao nhiêu requests/minute?**
   - Mặc định là 10 requests / 1 phút cho mỗi người dùng (API key bucket).
3. **Làm sao bypass limit cho admin?**
   - Ta có thể thêm một middleware check quyền hoặc phân hạng API Key. Nếu API key thuộc nhóm admin, ta bỏ qua (bypass) không gọi hàm kiểm tra rate limit hoặc gán một định mức quota cao hơn rất nhiều (ví dụ: vô hạn hoặc 10,000 req/min).

### Exercise 4.4: Logic Cost Guard triển khai bằng Redis
- Lưu trữ tổng tiền đã sử dụng trong ngày dưới dạng key với format: `budget:{user_id}:{date}`.
- Mỗi lần gọi LLM, tính toán số tokens tiêu thụ rồi cộng dồn chi phí dự tính vào key này trên Redis thông qua lệnh `INCRBYFLOAT`.
- Trước mỗi request, lấy giá trị hiện tại của key đó. Nếu vượt quá budget tối đa cho phép trong ngày (ví dụ: $1.00), từ chối xử lý và trả về lỗi `HTTP 402 Payment Required`.

---

## 📍 Part 5: Scaling & Reliability

### Exercise 5.1 & 5.2: Trả lời về Probes & Graceful Shutdown
1. **Liveness Probe (`/health`):** Xác định container có đang chạy bình thường không. Nếu API này trả về lỗi hoặc timeout liên tục, container orchestrator (như Docker Compose, Kubernetes) sẽ kill container cũ và tạo container mới để thay thế.
2. **Readiness Probe (`/ready`):** Xác định container đã sẵn sàng nhận traffic phục vụ người dùng chưa (chờ khởi động xong, đã ping thành công Redis và Database). Nếu chưa ready, Load Balancer sẽ rút instance này ra khỏi danh sách định tuyến, tránh gửi request của người dùng vào một server chưa hoạt động ổn định.
3. **Graceful Shutdown:** Khi nhận tín hiệu `SIGTERM`, server sẽ ngay lập tức thiết lập trạng thái `ready = False` để báo cho Load Balancer ngắt traffic tới nó. Sau đó, nó giữ tiến trình sống thêm một khoảng thời gian (ví dụ: 15-30 giây) để xử lý nốt các HTTP request đang chạy dở rồi mới chính thức đóng kết nối cơ sở dữ liệu và thoát.

---

## 📍 Part 6: Lab Complete - Deploy RAG API

### Kết quả triển khai
- **Platform sử dụng:** Railway
- **Service:** `api`
- **Public URL:** `https://api-production-ea3a.up.railway.app/`
- **Health check:** `https://api-production-ea3a.up.railway.app/health`
- **Endpoint hỏi đáp RAG:** `POST https://api-production-ea3a.up.railway.app/ask`

### Cấu hình production đã thiết lập
- **Docker build:** Dùng Dockerfile production để build image triển khai lên Railway.
- **Runtime port:** App đọc biến môi trường `PORT` do Railway cấp và chạy bằng `uvicorn`.
- **Security:** Đã cấu hình `AGENT_API_KEY` và `JWT_SECRET` trong Railway Variables.
- **RAG mode:** Sử dụng `RAG_GENERATION_PROVIDER=offline` để trả lời bằng pipeline RAG offline.
- **Storage:** Kết nối Redis Railway qua `REDIS_URL` để lưu session/history.

### Kết quả kiểm thử
- `/health` trả về `status: ok`.
- `/ask` trả lời được câu hỏi tiếng Việt.
- Response có kèm `sources`, `generation_provider`, `retrieval_source`, `session_id` và `turn`.
- Tiếng Việt hiển thị đúng khi gửi body bằng UTF-8.

### Lệnh kiểm thử đã dùng
```powershell
Invoke-RestMethod -Uri "https://api-production-ea3a.up.railway.app/health"

$body = @{ question = "sử dụng ma túy bị phạt thế nào?" } | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod -Uri "https://api-production-ea3a.up.railway.app/ask" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Headers @{ "X-API-Key" = "<AGENT_API_KEY>" } `
  -Body $bytes
```
