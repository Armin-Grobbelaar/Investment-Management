# =========================
# Stage 1: Build frontend
# =========================
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY investment_frontend/package*.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund
COPY investment_frontend/ ./
RUN rm -rf src/app/api/edit_data
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# =========================
# Stage 2: Final image
# =========================
FROM python:3.12-slim
WORKDIR /app

# ── System deps ──────────────────────────────────────────────────────────────
# Install build tools + minimal Chromium runtime libs (for Playwright).
# We do NOT use `playwright install --with-deps` (too large).
# TensorFlow/Keras are NOT bundled here — the backend connects to the
# host's existing tensorflow Docker container via TENSORFLOW_SERVER_URL.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev gcc git curl nodejs postgresql-client \
        # Minimal Chromium runtime libraries for Playwright
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
        libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
        libcairo2 libx11-6 libx11-xcb1 libxext6 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# ── Python packages ───────────────────────────────────────────────────────────
COPY investment_backend/requirements.docker.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.docker.txt \
    && playwright install chromium \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /root/.cache/pip /tmp/*

# FastAPI file/form upload routes require python-multipart. Kept as its own
# small layer so the heavy requirements layer above stays cached on rebuilds.
RUN pip install --default-timeout=1000 --no-cache-dir python-multipart \
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
