# =========================
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY investment_frontend/package*.json ./
RUN npm config set fetch-retry-mintimeout 20000 && npm config set fetch-retry-maxtimeout 120000 && npm install --legacy-peer-deps --no-audit --no-fund --fetch-timeout=300000
COPY investment_frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# =========================
# Stage 2: Final image
# =========================
FROM python:3.12-slim
WORKDIR /app

# ── System deps ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev gcc git curl nodejs postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ── Python packages ───────────────────────────────────────────────────────────
COPY investment_backend/requirements.docker.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.docker.txt \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /root/.cache/pip /tmp/*

RUN pip install --default-timeout=1000 --no-cache-dir python-multipart numpy pandas scipy scikit-learn numpy-financial statsmodels \
    && rm -rf /root/.cache/pip

# ── Application code ──────────────────────────────────────────────────────────
COPY investment_backend/ ./
COPY --from=frontend-build /app/frontend/.next/standalone ./frontend
COPY --from=frontend-build /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY investment_backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 3337 3037
ENV NODE_ENV=production PORT=3037 HOSTNAME="0.0.0.0"
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fs http://localhost:3337/health || exit 1
ENTRYPOINT ["./entrypoint.sh"]
