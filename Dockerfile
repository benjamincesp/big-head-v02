# Food Service 2025 Multi-Agent System Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Create necessary directories with proper permissions
RUN mkdir -p folders/general folders/exhibitors folders/visitors vector_stores /home/appuser/.cache
RUN chown -R appuser:appuser /app /home/appuser/.cache

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/transformers
ENV SENTENCE_TRANSFORMERS_HOME=/home/appuser/.cache/sentence-transformers

USER appuser

# Pre-download the sentence transformer model to avoid runtime download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/food-service/health || exit 1

# Start the application
CMD ["python", "api.py"]