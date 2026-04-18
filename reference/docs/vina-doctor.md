# Vina Doctor

## 1. Thiết lập môi trường (Backend - FastAPI)

Dự án sử dụng [uv](https://docs.astral.sh/uv/) làm Python package manager.

```bash
uv init
uv add dashscope
```

## 2. Triển khai Code mẫu (The "Heart" of Scribe)

Đây là cách bạn gửi một file âm thanh cuộc khám kèm theo Prompt để Qwen2-Audio vừa Transcribe vừa Extract dữ liệu y tế cùng lúc.

```python
import dashscope
from dashscope import MultiModalConversation

# Đặt API Key (Lấy từ console.aliyun.com)
dashscope.api_key = "YOUR_DASHSCOPE_API_KEY"


def process_medical_audio(audio_file_path):
    messages = [
        {
            "role": "system",
            "content": [{"text": "Bạn là trợ lý y khoa chuyên nghiệp. Hãy nghe và trích xuất thông tin y tế chính xác."}]
        },
        {
            "role": "user",
            "content": [
                {"audio": audio_file_path},
                {"text": "Hãy phân vai Bác sĩ và Bệnh nhân. Trích xuất: Triệu chứng, Chẩn đoán, và Thuốc. Trả về định dạng JSON."}
            ]
        }
    ]

    response = MultiModalConversation.call(model='qwen-audio-turbo', messages=messages)

    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        return f"Error: {response.code} - {response.message}"


# Sử dụng
# result = process_medical_audio("path/to/consultation.mp3")
```

## 3. Workflow tích hợp vào Full-stack

Để đảm bảo tiêu chí Execution & Solution Quality, hệ thống của bạn nên chạy theo luồng sau:

- **Frontend (Next.js):** Bác sĩ nhấn "Kết thúc", audio được đẩy lên S3 hoặc lưu tạm ở Backend.
- **Backend (FastAPI):** Nhận file, gọi hàm `process_medical_audio`.
- **Qwen API:** Xử lý đa phương thức (Audio + Prompt). Qwen sẽ không chỉ chuyển thành chữ mà còn hiểu ngữ cảnh y tế để lọc bỏ các đoạn nói chuyện phiếm.
- **Data Processing:** Backend nhận JSON từ Qwen, lưu vào Database và trả về Frontend để hiển thị bản nháp báo cáo.

## 4. Mẹo "Hack" để đạt điểm tối đa (Winning Tips)

### A. Xử lý đa ngôn ngữ (Multilingual Handling)

Đề bài yêu cầu EN/FR/AR/VN. Bạn không cần làm 4 hàm riêng. Hãy sửa Prompt:

> "Translate the final clinical report into English, French, Arabic, and Vietnamese. Maintain medical terminology accuracy for each language."

Qwen2-Audio làm việc này cực tốt trong một lượt phản hồi duy nhất.

### B. Tối ưu chi phí & Tốc độ

- **Model Choice:** Dùng `qwen-audio-turbo` cho các cuộc hội thoại ngắn để lấy tốc độ nhanh (phù hợp Demo). Dùng `qwen-audio-max` nếu file ghi âm dài và có nhiều thuật ngữ y khoa cực khó.
- **Audio Format:** Nên nén về `.mp3` hoặc `.m4a` trước khi gửi API để giảm latency truyền tải dữ liệu.

### C. Thêm lớp "Security" (Bảo mật)

Trước khi gửi audio, hãy chạy một script nhỏ (ML cơ bản) để kiểm tra xem file có chứa âm thanh hay không (VAD), tránh gửi file rác lên API gây lãng phí.

## 5. Tại sao cách này "thắng" tại Elfie Care?

- **Độ chính xác cao:** Qwen-Audio được huấn luyện để hiểu "ý định" đằng sau lời nói, giúp tránh lỗi khi bệnh nhân nói ngắc ngứ hoặc dùng từ địa phương.
- **Tính hành động (Actionability):** Vì bạn yêu cầu trả về JSON, hệ thống của bạn có thể tự động điền (auto-fill) vào các form thuốc, lịch hẹn, giúp bác sĩ tiết kiệm thời gian thực sự.

## 6. Cách triển khai "Winning Workflow" trên DashScope

Để thắng giải Healthcare Track, bạn không nên chỉ gọi API một cách đơn thuần. Hãy thiết lập theo cấu trúc Asynchronous (Bất đồng bộ) để đảm bảo UX mượt mà:

### Bước 1: Upload & Transcribe (Dùng Turbo)

Khi bác sĩ đang nói, bạn gửi từng đoạn audio ngắn (chunks) lên `qwen-audio-turbo`.

- **Mục tiêu:** Hiển thị chữ lên màn hình ngay lập tức (UX Clarity).
- **Kết quả:** Bác sĩ thấy AI đang "nghe" mình, tạo sự tin tưởng.

### Bước 2: Clinical Refinement (Dùng Max)

Khi kết thúc cuộc khám, bạn gửi toàn bộ file audio (hoặc bản transcript tổng) lên `qwen-audio-max`.

- **Mục tiêu:** Trích xuất JSON y khoa chuẩn (Clinical Correctness).
- **Prompt nâng cao:** "Dựa vào toàn bộ cuộc hội thoại, hãy điền vào mẫu SOAP, tìm mã ICD-10 và kiểm tra xem liều lượng thuốc có gì bất thường không."

Khi gọi DashScope, hãy ép AI trả về JSON ngay trong Prompt để Backend của bạn không bị "crash":

```python
prompt = """
Hãy đóng vai một thư ký y khoa.
Nghe file audio này và trả về kết quả DUY NHẤT dưới dạng JSON theo cấu trúc sau:
{
  "diagnosis": "...",
  "symptoms": ["s1", "s2"],
  "medications": [{"name": "...", "dosage": "..."}],
  "languages": {"vn": "...", "en": "...", "fr": "...", "ar": "..."}
}
"""

# Gọi model qwen-audio-max ở bước này để lấy JSON chuẩn nhất
```
