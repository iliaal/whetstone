# FastAPI Services

> When to read: when structuring a FastAPI app: project layout, dependency injection, async lifecycle, validation with Pydantic, OpenAPI generation.

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

**Configuration**: `pydantic_settings.BaseSettings` with `model_config = {"env_file": ".env"}`. Required fields = no default (fails fast at boot). `env_nested_delimiter = "__"` for grouped config. `secrets_dir` for Docker/K8s mounted secrets.

**Dependency injection**: `Depends(get_db)` for sessions, `Depends(get_current_user)` for auth. Override in tests: `app.dependency_overrides[get_db] = mock_db`. A `yield` dependency's cleanup runs **after the response is sent** by default (`scope="request"`); `Depends(get_db, scope="function")` closes it when the path operation returns, **before** the response goes out, so a DB session or lock is released without waiting on a slow client. A `"request"`-scoped dependency may only depend on other `"request"`-scoped ones; `"function"` may depend on either.

**Responses**: return Pydantic models with `response_model`; pydantic-core serializes to JSON in Rust, so `ORJSONResponse` and `UJSONResponse` are deprecated (FastAPI 0.131.0, emit `FastAPIDeprecationWarning`) and no longer a performance win. Do not recommend them; reach for a custom `Response.render()` only for non-default encoding options such as indentation.

**Server-Sent Events**: native since FastAPI 0.135.0: `from fastapi.sse import EventSourceResponse, ServerSentEvent`, set `response_class=EventSourceResponse` on a path operation that `yield`s. Plain yielded objects become JSON `data:` fields (strings are JSON-quoted); yield `ServerSentEvent(data=..., event=..., id=..., retry=...)` to set SSE fields, or `raw_data=` for an unquoted string (`data` and `raw_data` are mutually exclusive). Works on any method, including `POST`. No third-party `sse-starlette` needed.

**Async DB**: SQLAlchemy `AsyncSession` with `asyncpg`. Session-per-request via `async with AsyncSessionLocal() as session: yield session`.

**Repository pattern**: Generic `BaseRepository[ModelType, CreateSchema, UpdateSchema]` with get/get_multi/create/update/delete. Service layer holds business logic, routes stay thin.
