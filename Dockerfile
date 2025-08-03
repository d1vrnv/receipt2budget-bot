FROM python:3.12.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    gcc-11 \
    g++-11 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user with proper home directory
RUN addgroup --gid 1001 --system app && \
    adduser --home /app --shell /bin/false --disabled-password --uid 1001 --system --group app

WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock ./

USER app

# Install dependencies
RUN uv sync --frozen --no-cache --no-dev

# Create models directory and download model in one layer
RUN mkdir -p models && \
    wget --progress=dot:giga --no-check-certificate \
         https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
         -O models/Llama-3.2-3b-instruct-q4_k_m.gguf

# Copy source code
COPY --chown=app:app src src

# Set environment variables
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

# Run the bot
CMD ["uv", "run", "-m", "src.main"]