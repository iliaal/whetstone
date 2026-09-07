# Docker & Containerization

Load this reference when reviewing a Dockerfile, docker-compose setup, or container image build. Not needed for CI/CD or observability-only reviews.

## Dockerfile Best Practices

- **Multi-stage builds**: separate builder from runtime — only copy artifacts into final stage
- **Minimal base images**: the current LTS/stable slim or alpine variant of the runtime (e.g. `node:<current-LTS>-alpine`, `python:<current>-slim`, `php:<current>-fpm-alpine`) — not full images
- **Layer ordering**: least-changing layers first (OS packages → dependency install → copy source → build)
- **Dependency caching**: copy lockfile first, install deps, then copy source (cache deps layer separately)
- **Non-root user**: create the account, then switch by **numeric** id — `RUN adduser -D -u 10001 app` then `USER 10001:10001`. A name-based `USER app` resolves against the image's own passwd database, so it breaks when the base image changes distro and defeats host-side uid checks and `runAsNonRoot` admission rules
- **No secrets in image**: reserve build arguments for non-secret configuration. Pass build credentials with `docker build --secret` and consume them with `RUN --mount=type=secret`, or use SSH mounts for SSH credentials; never copy mounted secrets into build artifacts. Mount runtime secrets or retrieve them from a secrets manager.
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
- Drop ambient privilege at runtime: `security_opt: ["no-new-privileges:true"]`, `cap_drop: [ALL]` (add back only the capabilities actually needed), and a finite `pids_limit` so a fork bomb inside the container cannot exhaust host PIDs
- Pair `--read-only` with an explicit writable `tmpfs` for scratch paths, mounted `noexec` and owned by the runtime uid — a read-only root filesystem with a writable, executable scratch mount buys little
- Default the network off (`network_mode: none`) for anything that does not need egress, and add access through a visibly named service or profile. Never make network reach an environment-variable default that a misconfigured deploy switches on silently

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
