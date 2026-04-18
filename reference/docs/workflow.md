# Workflow

Dưới đây là quy trình hoạt động thực tế (Operational Workflow) mà bạn nên trình bày trong dự án:

## 1. Giai đoạn: Bắt đầu tư vấn (The Warm-up)

- **Hành động:** Bác sĩ mở ứng dụng và nhấn nút "Start Recording".
- **Trải nghiệm:** Thay vì ngồi sau màn hình máy tính, bác sĩ xoay ghế lại đối diện với bệnh nhân.
- **AI Role:** Hệ thống bắt đầu thu âm âm thanh đa hướng, lọc bỏ tiếng ồn trắng của phòng máy lạnh hoặc tiếng máy móc xung quanh.

## 2. Giai đoạn: Thăm khám (The Human Interaction)

Đây là lúc giá trị của AI tỏa sáng nhất.

- **Bác sĩ:** Hỏi han về triệu chứng, tiền sử, và tiến hành khám thực thể (nghe tim, đo huyết áp). Bác sĩ có thể nói ra các quan sát của mình thành tiếng (ví dụ: "Phổi trong, không rale").
- **Bệnh nhân:** Tự do kể về tình trạng sức khỏe mà không bị ngắt quãng bởi tiếng gõ bàn phím.
- **AI Role:** Chạy ngầm (Background process). Nó thực hiện Diarization (phân biệt giọng bác sĩ/bệnh nhân) và Transcribe theo thời gian thực.

## 3. Giai đoạn: Phân tích & Trích xuất (The Intelligence)

Ngay khi cuộc hội thoại kết thúc hoặc diễn ra được một phần:

- **AI Role:**
  - **Phân loại:** Tự động đưa thông tin vào các mục tương ứng: Lý do khám, Triệu chứng, Tiền sử gia đình, Thuốc đang dùng.
  - **Chuẩn hóa:** Chuyển các cách nói dân dã của bệnh nhân (ví dụ: "đau như kim châm ở ngực") thành thuật ngữ y khoa chuẩn (ví dụ: "sharp chest pain").
  - **Đối chiếu:** So sánh với cơ sở dữ liệu y khoa để gợi ý mã bệnh (ICD-10).

## 4. Giai đoạn: Kiểm duyệt & Phê duyệt (The Doctor's Review)

Đây là bước Human-in-the-loop cực kỳ quan trọng để đảm bảo tính an toàn y tế.

- **Hành động:** Bác sĩ nhìn vào màn hình Dashboard. Một bản nháp báo cáo (Medical Report) theo định dạng SOAP đã được điền sẵn khoảng 80-90%.
- **Chỉnh sửa:** Bác sĩ chỉ cần kiểm tra nhanh, sửa lại những chỗ AI hiểu lầm (nếu có) hoặc bổ sung các chỉ định xét nghiệm.
- **AI Role:** Cập nhật bản nháp dựa trên các chỉnh sửa của bác sĩ để "học" cho lần sau.

## 5. Giai đoạn: Kết thúc & Lưu trữ (The Completion)

- **Hành động:** Bác sĩ nhấn "Finalize".
- **Kết quả:**
  - **Hồ sơ bệnh viện:** Báo cáo được đẩy thẳng vào hệ thống quản lý (EMR/HIS).
  - **Cho bệnh nhân:** Một bản tóm tắt dễ hiểu (Patient-friendly version) được gửi qua App hoặc in ra, dặn dò lịch tái khám và cách dùng thuốc.
- **AI Role:** Tự động dịch báo cáo sang các ngôn ngữ khác (nếu bệnh nhân là người nước ngoài) theo yêu cầu của đề bài Challenge 1.
