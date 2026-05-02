# Docker & Containerization

Load this reference when reviewing a Dockerfile, docker-compose setup, or container image build. Not needed for CI/CD or observability-only reviews.

## Dockerfile Best Practices

- **Multi-stage builds**: separate builder from runtime — only copy artifacts into final stage
- **Minimal base images**: `node:20-alpine`, `python:3.12-slim`, `php:8.3-fpm-alpine` — not full images
- **Layer ordering**: least-changing layers first (OS packages → dependency install → copy source → build)
- **Dependency caching**: copy lockfile first, install deps, then copy source (cache deps layer separately)
- **Non-root user**: `RUN adduser -D app && USER app` — never run as root in production
- **No secrets in image**: use build args for build-time only, mount secrets at runtime
- **.dockerignore**: exclude `.git/`, `node_modules/`, `.env`, test files, docs

## Image Optimization

- Pin base image digests in production (`node:20-alpine@sha256:...`) for reproducibility
- Remove build tools, caches, package manager caches in the same RUN layer (`apt-get clean && rm -rf /var/lib/apt/lists/*`)
- Use `COPY --from=builder` to cherry-pick artifacts — don't copy entire build directory
- Target image size: < 100MB for Node.js, < 150MB for Python, < 200MB for PHP

## Container Security

- Scan images with Trivy or Grype in CI — fail on HIGH/CRITICAL vulnerabilities
- Pin dependencies (lockfiles committed) — no `latest` tags for base images
- Read-only filesystem where possible (`--read-only`), mount writable volumes only where needed
- Health checks: `HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1`
- Resource limits: always set CPU and memory limits to prevent noisy-neighbor issues

## Graceful Shutdown

- Handle `SIGTERM` — stop accepting new requests, finish in-flight work, close DB connections
- Set `STOPSIGNAL SIGTERM` in Dockerfile
- Shutdown timeout: 30 seconds (match orchestrator's grace period)
- Drain connections before exit — return 503 on health check during shutdown

## Docker Compose (Development)

- One `docker-compose.yml` per project for local development
- Match production topology: app + database + cache + queue
- Use volumes for source code (hot reload), named volumes for data persistence
- Set `depends_on` with health check conditions
- Environment files: `.env.docker` separate from `.env` (different connection strings)
