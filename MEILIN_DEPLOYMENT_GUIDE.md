# Hướng dẫn Deploy MeiLin Project trên Ubuntu với Cloudflared

## Trả lời câu hỏi của bạn:

### 1. "Bổ sung thêm 1 container cũng chạy qua Cloudflared tunnel có khó không?"
**KHÔNG KHÓ** - Rất dễ dàng! Chỉ cần 2 bước:

#### Bước 1: Thêm service vào `docker-compose.yml`
```yaml
your-new-service:
  image: your-image:latest
  container_name: your-service
  restart: unless-stopped
  networks:
    - meilin-network
  # ... other config
```

#### Bước 2: Thêm ingress rule vào `cloudflared/config.yml`
```yaml
ingress:
  # Existing rules...
  - hostname: your-service.truongcongdinh.org
    service: http://your-service:port
```

### 2. "Chạy nền tảng MeiLin trên Ubuntu server"
Đã sẵn sàng! Tôi đã tạo đầy đủ:

## Các file đã tạo:

### 1. **Docker Configuration**
- `docker-compose.yml` - Cấu hình 5 services:
  - `meilin-api` - FastAPI server (port 5000)
  - `meilin-telegram` - Telegram bot (optional)
  - `meilin-youtube` - YouTube livestream (optional)
  - `cloudflared` - Cloudflare tunnel
  - `chromadb` - Vector database (optional)

- `Dockerfile` - Build image cho MeiLin

### 2. **Cloudflared Configuration**
- `cloudflared/config.yml` - Cấu hình tunnel với 4 domains:
  - `meilin.truongcongdinh.org` → API server
  - `telegram-meilin.truongcongdinh.org` → Telegram bot
  - `youtube-meilin.truongcongdinh.org` → YouTube livestream
  - `chroma-meilin.truongcongdinh.org` → ChromaDB

### 3. **Deployment Scripts**
- `deploy-ubuntu.sh` - Script tự động deploy trên Ubuntu
- Cấp quyền thực thi: `chmod +x deploy-ubuntu.sh`

## Các bước triển khai:

### Bước 1: Chuẩn bị Ubuntu server
```bash
# Copy project to Ubuntu
scp -r . user@your-server:/path/to/meilin-project
```

### Bước 2: Chạy deployment script
```bash
cd /path/to/meilin-project
chmod +x deploy-ubuntu.sh
./deploy-ubuntu.sh
```

### Bước 3: Cấu hình Cloudflare
1. Đăng nhập Cloudflare Dashboard
2. Zero Trust → Networks → Tunnels
3. Tạo tunnel `meilin-tunnel`
4. Download credentials → `cloudflared/meilin-tunnel-credentials.json`
5. Thêm DNS records cho các domains

### Bước 4: Cấu hình API keys
Chỉnh sửa file `.env`:
```env
DEEPSEEK_API_KEY=your_key_here
# Other API keys...
```

## Kiến trúc hệ thống:

```
┌─────────────────────────────────────────────────┐
│            Cloudflare Tunnel                    │
│  meilin.truongcongdinh.org  →  cloudflared     │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            Docker Network                       │
│  ┌─────────────┐  ┌─────────────┐              │
│  │ meilin-api  │  │  telegram   │              │
│  │   :5000     │  │    bot      │              │
│  └──────┬──────┘  └──────┬──────┘              │
│         │                 │                     │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────────┐ │
│  │  youtube    │  │  chromadb   │  │  ...    │ │
│  │ livestream  │  │   :8000     │  │         │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
```

## Quản lý hệ thống:

```bash
# Xem trạng thái
docker-compose ps

# Xem logs
docker-compose logs
docker-compose logs meilin-api

# Dừng hệ thống
docker-compose down

# Khởi động lại
docker-compose restart

# Cập nhật
git pull
docker-compose build --no-cache
docker-compose up -d
```

## Thêm container mới (Ví dụ: Database):

### 1. Thêm vào docker-compose.yml:
```yaml
postgres:
  image: postgres:15
  container_name: meilin-postgres
  environment:
    POSTGRES_DB: meilin
    POSTGRES_USER: meilin
    POSTGRES_PASSWORD: password123
  volumes:
    - ./postgres_data:/var/lib/postgresql/data
  networks:
    - meilin-network
```

### 2. Thêm vào cloudflared config:
```yaml
ingress:
  # Existing rules...
  - hostname: db-meilin.truongcongdinh.org
    service: http://postgres:5432
```

## Xử lý sự cố:

### Cloudflared không kết nối:
```bash
# Check logs
docker-compose logs cloudflared

# Check credentials
ls -la cloudflared/

# Test tunnel manually
docker exec meilin-cloudflared cloudflared tunnel list
```

### API không hoạt động:
```bash
# Check API health
curl http://localhost:5000/

# Check environment variables
docker exec meilin-api env | grep API_KEY

# Check dependencies
docker exec meilin-api python -c "import chromadb; print('ChromaDB OK')"
```

## Kết luận:

✅ **Dễ dàng thêm container mới** - Chỉ cần 2 bước đơn giản  
✅ **Đã sẵn sàng deploy trên Ubuntu** - Có script tự động  
✅ **Cloudflared tích hợp sẵn** - Public access qua domain  
✅ **Kiến trúc modular** - Dễ mở rộng và quản lý  

Hệ thống MeiLin đã sẵn sàng để chạy trên Ubuntu server với Cloudflared tunnel!
