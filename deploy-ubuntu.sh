#!/bin/bash

echo "=========================================="
echo "   DEPLOY MEILIN PROJECT ON UBUNTU"
echo "=========================================="

# 1. Check prerequisites
echo "[1/6] Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✓ Docker installed. Please log out and log back in or run: newgrp docker"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

echo "✓ Docker and Docker Compose ready"

# 2. Create necessary directories
echo "[2/6] Creating directories..."
mkdir -p cloudflared chroma_data audio_cache database logs
mkdir -p static/wake_responses static/ambient_responses static/ambient_behaviors

echo "✓ Directories created"

# 3. Check Cloudflared configuration
echo "[3/6] Checking Cloudflared configuration..."
if [ ! -f "cloudflared/config.yml" ]; then
    echo "⚠ Cloudflared config.yml not found. Using default config."
    # config.yml already created
fi

if [ ! -f "cloudflared/meilin-tunnel-credentials.json" ]; then
    echo "⚠ Cloudflared credentials not found."
    echo "Please create a tunnel on Cloudflare Dashboard:"
    echo "1. Go to https://dash.cloudflare.com/"
    echo "2. Zero Trust → Networks → Tunnels"
    echo "3. Create tunnel: meilin-tunnel"
    echo "4. Download credentials to cloudflared/meilin-tunnel-credentials.json"
    echo ""
    echo "Or use existing tunnel:"
    echo "cp /path/to/existing/credentials.json cloudflared/meilin-tunnel-credentials.json"
    read -p "Press Enter after adding credentials..."
fi

# 4. Setup environment variables
echo "[4/6] Setting up environment..."
if [ ! -f ".env" ]; then
    echo "⚠ .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from .env.example"
        echo "Please edit .env and add your API keys"
    else
        echo "✗ .env.example not found. Creating basic .env..."
        cat > .env << EOF
# MeiLin API Keys
DEEPSEEK_API_KEY=your_deepseek_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# GOOGLE_API_KEY=your_google_api_key_here
# ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Telegram
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Owner Recognition
OWNER_USER_ID=your_youtube_channel_id_here
OWNER_USERNAME=YourName

# ChromaDB Cloud (optional)
# CHROMADB_API_URL=your_chromadb_url_here
# CHROMADB_API_TOKEN=your_chromadb_token_here

# Cloudflared Tunnel ID
CLOUDFLARED_TUNNEL_ID=your_tunnel_id_here
EOF
        echo "✓ Created basic .env file"
    fi
    echo "⚠ Please edit .env file and add your API keys before continuing"
    read -p "Press Enter after editing .env..."
fi

# 5. Build and start containers
echo "[5/6] Building and starting containers..."
echo "This may take a few minutes on first run..."

# Build Docker image
docker-compose build --no-cache

# Start services
docker-compose up -d

echo "✓ Containers started"

# 6. Check status
echo "[6/6] Checking deployment status..."
sleep 10  # Wait for containers to start

echo ""
echo "=========================================="
echo "   DEPLOYMENT STATUS"
echo "=========================================="

# Check container status
docker-compose ps

echo ""
echo "=========================================="
echo "   ACCESS INSTRUCTIONS"
echo "=========================================="
echo ""
echo "🌐 Local Access:"
echo "   API Server:    http://localhost:5000"
echo "   API Docs:      http://localhost:5000/docs"
echo "   ChromaDB:      http://localhost:8000 (if enabled)"
echo ""
echo "🌐 Cloudflare Tunnel (Public Access):"
echo "   Main API:      https://meilin.truongcongdinh.org"
echo "   Telegram:      https://telegram-meilin.truongcongdinh.org"
echo "   YouTube:       https://youtube-meilin.truongcongdinh.org"
echo "   ChromaDB:      https://chroma-meilin.truongcongdinh.org"
echo ""
echo "🔧 Management Commands:"
echo "   View logs:     docker-compose logs"
echo "   View logs (service): docker-compose logs meilin-api"
echo "   Stop:          docker-compose down"
echo "   Restart:       docker-compose restart"
echo "   Update:        git pull && docker-compose build --no-cache && docker-compose up -d"
echo ""
echo "📋 Service Information:"
echo "   - meilin-api:      FastAPI server (port 5000)"
echo "   - meilin-telegram: Telegram bot (optional)"
echo "   - meilin-youtube:  YouTube livestream (optional)"
echo "   - cloudflared:     Cloudflare tunnel"
echo "   - chromadb:        Vector database (optional)"
echo ""
echo "⚠ IMPORTANT:"
echo "   1. Ensure Cloudflared tunnel is configured on Cloudflare Dashboard"
echo "   2. Add DNS records for your domains pointing to the tunnel"
echo "   3. Check logs if services don't start: docker-compose logs"
echo ""
echo "✅ Deployment complete!"
