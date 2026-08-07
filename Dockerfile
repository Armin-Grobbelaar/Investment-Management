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
COPY investment_backend/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc git curl nodejs \
    && pip install --default-timeout=1000 --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/*
COPY investment_backend/ ./
COPY --from=frontend-build /app/frontend/.next/standalone ./frontend
COPY --from=frontend-build /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY investment_backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
EXPOSE 3337 3000
ENV NODE_ENV=production PORT=3000 HOSTNAME="0.0.0.0"
ENTRYPOINT ["./entrypoint.sh"]
