

# ----- Stage 1: builder ----------------------------------------------------
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build toolchain for any packages needing compilation (removed in runtime stage).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create an isolated virtualenv so the runtime stage copies a clean tree.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# ----- Stage 2: runtime ----------------------------------------------------
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="TalentMind" \
      org.opencontainers.image.description="Enterprise Candidate Intelligence Platform" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    TALENTMIND_ENV=production \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# curl is used by the container HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 talentmind

# Copy the prebuilt virtualenv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy the application (see .dockerignore for what is excluded).
COPY --chown=talentmind:talentmind . /app

# Writable runtime directories owned by the non-root user.
RUN mkdir -p /app/data /app/outputs /app/logs \
    && chown -R talentmind:talentmind /app/data /app/outputs /app/logs

USER talentmind

EXPOSE 8501

# Streamlit exposes a health endpoint at /_stcore/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py"]
CMD ["--server.port=8501", "--server.address=0.0.0.0"]
