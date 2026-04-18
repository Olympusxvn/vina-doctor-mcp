vina-doctor-agent/
├── ai_engine/                # "Trái tim" của hệ thống (Python)
│   ├── processors/           # Xử lý dữ liệu thô
│   │   ├── audio.py          # Whisper, VAD, Diarization
│   │   └── text_cleaner.py   # Anonymization (ẩn danh hóa PII)
│   ├── agents/               # LLM Logic (Qwen)
│   │   ├── extractor.py      # Trích xuất thông tin y khoa (JSON)
│   │   ├── reporter.py       # Tạo báo cáo đa ngôn ngữ
│   │   └── prompts.py        # Quản lý Master Prompts (để riêng cho dễ sửa)
│   └── utils/                # Helper functions cho AI
│
├── backend/                  # API Layer (FastAPI/Node.js)
│   ├── api/                  # Routes (v1/consultations, v1/reports)
│   ├── core/                 # Config, Security, Database connection
│   ├── schemas/              # Pydantic models (định nghĩa cấu trúc dữ liệu y tế)
│   └── storage/              # Lưu trữ tạm thời audio/PDF (local hoặc cloud)
│
├── frontend/                 # UI/UX Layer (Next.js/React + Tailwind)
│   ├── components/           # Dashboard, AudioPlayer, ReportViewer
│   ├── hooks/                # Xử lý state, gọi API
│   └── styles/               # Giao diện y tế (Sạch sẽ, tin cậy)
│
├── data/                     # Dữ liệu phục vụ thử nghiệm
│   ├── samples/              # File audio mẫu (VN, EN, FR)
│   └── medical_terms/        # Từ điển thuật ngữ y khoa (JSON/CSV)
│
├── docker-compose.yml        # Triển khai nhanh cho giám khảo xem
├── .env.example              # Chứa API Keys (Qwen 2.5 audio)
└── README.md                 # Tài liệu hướng dẫn, sơ đồ kiến trúc

