# Investment App Dockerization

This project is optimized for a low-disk space environment (~8GB) and uses a multi-stage standalone build for the frontend and a trimmed Python backend.

## 🚀 Quick Start (Local Docker)

1. **Prerequisites**: 
   - Docker & Docker Compose installed.
   - Local PostgreSQL running on port 5432 (database: `Investments`).

2. **Configuration**:
   Update `docker-compose.yml` environment variables (e.g., `POSTGRES_PASSWORD`) to match your local setup.

3. **Build & Run**:
   ```bash
   docker-compose up -d --build
   ```

## 🏗️ Docker Features

- **Small Image Size**: Uses Next.js `standalone` output and removed ~3GB of unused heavy ML libraries (`torch`, `transformers`, etc.).
- **Host Networking**: Uses `network_mode: host` to access your existing databases on `localhost:5432` and `localhost:5433` without complex networking.
- **Auto-Cleanup**: The Dockerfile and Jenkinsfile are configured to clean up caches and intermediate layers immediately.

## 🤖 Jenkins CI/CD

The included `Jenkinsfile` automates:
1. **Cleanup**: Prunes old docker data to free up space before building.
2. **Build**: Builds the optimized image.
3. **Push**: Pushes to DockerHub (requires `dockerhub-credentials` ID in Jenkins).
4. **Cleanup**: Prunes dangling images after push.

## 🔧 Optimization Notes

If disk space is still an issue during build:
- Run `docker system prune -a` before building.
- Check `df -h /` regularly.
- The build will consume ~2-3GB of space temporarily during the build process.
