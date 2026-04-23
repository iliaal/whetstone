## FastAPI Services

**Project structure:**
```
app/
├── api/v1/endpoints/    # Route handlers
├── core/                # config.py, security.py, database.py
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic request/response
├── services/            # Business logic
├── repositories/        # Data access (generic CRUD base)
└── main.py              # Lifespan, middleware, router includes
```

**Lifespan** for startup/shutdown: `@asynccontextmanager async def lifespan(app):`

**Configuration** -- `pydantic_settings.BaseSettings` with `model_config = {"env_file": ".env"}`. Required fields = no default (fails fast at boot). `env_nested_delimiter = "__"` for grouped config. `secrets_dir` for Docker/K8s mounted secrets.

**Dependency injection** -- `Depends(get_db)` for sessions, `Depends(get_current_user)` for auth. Override in tests: `app.dependency_overrides[get_db] = mock_db`.

**Async DB** -- SQLAlchemy `AsyncSession` with `asyncpg`. Session-per-request via `async with AsyncSessionLocal() as session: yield session`.

**Repository pattern** -- Generic `BaseRepository[ModelType, CreateSchema, UpdateSchema]` with get/get_multi/create/update/delete. Service layer holds business logic, routes stay thin.
