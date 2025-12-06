FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (ffmpeg for audio processing)
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only FIRST (saves ~8GB vs CUDA version)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install (excluding torch since we installed it above)
COPY requirements.txt .
RUN grep -v "^torch" requirements.txt > requirements_no_torch.txt && \
    pip install --no-cache-dir -r requirements_no_torch.txt && \
    rm requirements_no_torch.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p audio_cache database logs static/wake_responses static/ambient_responses static/ambient_behaviors

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command (API server)
CMD ["python", "meilin_api_server.py"]