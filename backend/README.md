# CV Scanner HR

FastAPI MVC + 1 file HTML — gọn, chạy nhanh.

## Cấu trúc MVC

```text
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Cấu hình
│   ├── controllers/         # Routes (Controller)
│   │   ├── page_controller.py
│   │   ├── cv_controller.py
│   │   └── candidate_controller.py
│   ├── models/              # Pydantic schemas (Model)
│   │   └── schemas.py
│   ├── views/               # Giao diện
│   │   └── index.html       # 1 file HTML duy nhất
│   └── services/            # Business logic
│       ├── cv_extractor.py
│       ├── ai_parser.py
│       ├── age_calculator.py
│       └── storage.py
├── requirements.txt
└── .env.example
```

## Cấu hình AI

### Dùng DeepSeek (khuyến nghị — rẻ, API tương thích OpenAI)

Sửa file `.env` ở thư mục gốc:

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...          # https://platform.deepseek.com/api_keys
DEEPSEEK_MODEL=deepseek-chat
```

### Dùng OpenAI / ChatGPT

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...            # https://platform.openai.com/api-keys
OPENAI_MODEL=gpt-4o-mini
```

Sau khi đổi `.env`, restart: `docker compose down && docker compose up -d`

## Chạy bằng Docker (khuyến nghị)

```bash
# 1. Tạo file .env và điền API key (DeepSeek hoặc OpenAI)
cp .env.example .env

# 2. Build & chạy
docker compose up -d --build

# 3. Xem log
docker compose logs -f
```

Mở http://localhost:8000

Dừng app: `docker compose down`  
Dừng và xóa dữ liệu CV: `docker compose down -v`

## Chạy local (không Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # thêm OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

## API

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Giao diện HTML |
| POST | `/api/cv/upload` | Upload & phân tích CV |
| POST | `/api/candidate/save` | Lưu ứng viên + CV |
| GET | `/api/candidate/export` | Tải Excel |

## Lưu trữ

- Không cần Google API: file CV lưu tại `data/cvs/`, metadata tại `data/candidates.json`
- Có API key (DeepSeek/OpenAI): AI phân tích CV chính xác
- Không có key hoặc API lỗi: fallback regex tự trích xuất cơ bản
