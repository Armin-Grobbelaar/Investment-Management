# =========================
# Stage 1: Build frontend
# =========================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY investment_frontend/package*.json ./
RUN npm install
COPY investment_frontend/ ./
RUN npm run build

# =========================
# Stage 2: Backend + final image
# =========================
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for psycopg2, matplotlib, pg_isready, Node.js
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev python3-dev gcc git curl postgresql-client nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY investment_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY investment_backend/ ./backend

# Copy frontend build artifacts
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/

# Install frontend dependencies in the final image
WORKDIR /app/frontend
RUN npm install --production

# Copy entrypoint script
COPY investment_backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set workdir back to /app
WORKDIR /app

# Expose ports
EXPOSE 3337 3000

# Start script
ENTRYPOINT ["./entrypoint.sh"]