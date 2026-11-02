# ContextIQ Backend — Dockerfile
# ================================
# Build:  docker build -t contextiq-backend .
# Run:    docker run -p 8000:8000 --env-file .env contextiq-backend
#
# Design decisions:
#   python:3.11-slim   — minimal base image; avoids dev tools and compilers
#                         that inflate the final image by ~600MB.
#   --no-cache-dir     — don't write pip's HTTP/wheel cache to the layer;
#                         shaves ~50MB off the final image size.
#   Non-root user      — running as root inside a container is a security
#                         anti-pattern. The 'app' user owns only /app.
#   COPY requirements first — Docker's layer cache re-uses the pip install
#                         layer as long as requirements.txt hasn't changed,
#                         making rebuilds after code-only changes very fast.

FROM python:3.11-slim

# Create a non-root user for runtime security
RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Install dependencies first (cache-friendly layer ordering)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Transfer ownership to the non-root user
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Uvicorn serves the FastAPI app.
# --host 0.0.0.0 binds to all interfaces (required inside a container).
# --port 8000 matches the EXPOSE above.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

