FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
COPY check.py .

RUN groupadd --system appgroup && useradd --system --create-home --gid appgroup appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

EXPOSE 8000
CMD ["python", "-m", "app.mcp_server"]
