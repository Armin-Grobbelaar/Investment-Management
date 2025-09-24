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

# Install system dependencies for psycopg2 and matplotlib
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev python3-dev gcc git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY investment_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY investment_backend/ ./backend

# Copy frontend build
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/

# Copy entrypoint script
COPY investment_backend/entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose ports
EXPOSE 3337  # FastAPI
EXPOSE 3000  # Next.js

# Start script
ENTRYPOINT ["./entrypoint.sh"]
