# Axum HTTP Services

Patterns for building production HTTP services with `axum` + `tokio` + `tower`.

## Project Layout

```
src/
  main.rs           # Entrypoint: config load, tracing init, server bind, graceful shutdown
  app.rs            # Router assembly: `pub fn router(state: AppState) -> Router`
  state.rs          # AppState struct (pools, clients, config)
  error.rs          # AppError enum + IntoResponse impl
  routes/
    mod.rs
    users.rs        # One module per resource
    health.rs
  services/         # Business logic, no HTTP types
  repo/             # Data access (sqlx), no HTTP types
  config.rs
  telemetry.rs      # tracing + metrics setup
tests/
  api.rs           # Integration tests hitting the router directly
```

Rules mirror the layered architecture from `ia-nodejs-backend`:
- Routes parse + call services + format response. No business logic.
- Services never import from `axum` or `http`. No HTTP status codes leak in.
- Repos never construct `AppError` variants that map to HTTP — they return typed storage errors that services convert.

## AppState

```rust
#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::PgPool,
    pub http: reqwest::Client,
    pub config: Arc<Config>,
}
```

`Clone` is cheap because the expensive members are `Arc` inside. Inject with `State<AppState>` extractor — don't use globals or `OnceCell`.

## Error Type

```rust
use axum::{http::StatusCode, response::{IntoResponse, Response}, Json};
use serde_json::json;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("not found")]
    NotFound,
    #[error("invalid input: {0}")]
    Validation(String),
    #[error("unauthorized")]
    Unauthorized,
    #[error(transparent)]
    Sqlx(#[from] sqlx::Error),
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, code) = match &self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "not_found"),
            AppError::Validation(_) => (StatusCode::BAD_REQUEST, "validation"),
            AppError::Unauthorized => (StatusCode::UNAUTHORIZED, "unauthorized"),
            AppError::Sqlx(_) | AppError::Other(_) => {
                tracing::error!(error = ?self, "internal error");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal")
            }
        };
        let body = Json(json!({
            "error": { "code": code, "message": self.to_string() }
        }));
        (status, body).into_response()
    }
}
```

- One error envelope shape across every handler. Callers parse `.error.code` once.
- Log the full error with `?self` for `INTERNAL_SERVER_ERROR` paths; never leak internal messages to the client.
- Use `?` in handlers freely — `From` impls convert `sqlx::Error`, `anyhow::Error` into `AppError`.

## Handlers

```rust
#[tracing::instrument(skip(state), fields(user_id))]
pub async fn get_user(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>, AppError> {
    tracing::Span::current().record("user_id", %id);
    let user = state.users.find(id).await?.ok_or(AppError::NotFound)?;
    Ok(Json(user.into()))
}
```

- Handlers take extractors first, body last. Extractors run in order; the body extractor must be last (it consumes the request).
- Return `Result<Json<T>, AppError>` for JSON endpoints, `Result<impl IntoResponse, AppError>` for flexible responses.
- Use `#[tracing::instrument(skip(state))]` on every handler — skip the state so secrets don't land in logs.

## Validation

```rust
use validator::Validate;

#[derive(Deserialize, Validate)]
pub struct CreateUser {
    #[validate(length(min = 1, max = 100))]
    pub name: String,
    #[validate(email)]
    pub email: String,
}

pub async fn create_user(
    State(state): State<AppState>,
    Json(body): Json<CreateUser>,
) -> Result<(StatusCode, Json<UserResponse>), AppError> {
    body.validate().map_err(|e| AppError::Validation(e.to_string()))?;
    let user = state.users.create(body.into()).await?;
    Ok((StatusCode::CREATED, Json(user.into())))
}
```

Or centralize via a `ValidatedJson<T>` extractor so every handler calls `.validate()` without repetition.

## Middleware

```rust
use tower::ServiceBuilder;
use tower_http::{trace::TraceLayer, timeout::TimeoutLayer, cors::CorsLayer};

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health::shallow))
        .route("/ready",  get(health::deep))
        .nest("/users", users::routes())
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(TimeoutLayer::new(Duration::from_secs(30)))
                .layer(CorsLayer::permissive())
                .into_inner(),
        )
        .with_state(state)
}
```

Middleware order: tracing → timeout → rate limit → auth → CORS → handler. Tracing *outside* the timeout so you see timed-out requests.

## Graceful Shutdown

```rust
async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c().await.expect("install ctrl+c handler");
    };
    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("install sigterm handler")
            .recv().await;
    };
    tokio::select! { _ = ctrl_c => {}, _ = terminate => {} }
    tracing::info!("shutdown signal received");
}

// main.rs
let listener = tokio::net::TcpListener::bind(&config.addr).await?;
axum::serve(listener, app::router(state))
    .with_graceful_shutdown(shutdown_signal())
    .await?;
```

- Drain in-flight requests up to a budget (30s typical), then hard-exit.
- Close DB pools and flush telemetry *after* the server returns, before `main` exits.

## Testing

```rust
use axum::body::Body;
use axum::http::{Request, StatusCode};
use tower::ServiceExt; // for `.oneshot()`

#[tokio::test]
async fn get_user_returns_404_for_unknown_id() {
    let state = test_state().await;
    let app = app::router(state);
    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/users/{}", Uuid::new_v4()))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
```

- Exercise the router directly with `tower::ServiceExt::oneshot` — no TCP bind needed, fast and deterministic.
- `sqlx::test` macro gives each test an isolated database via transactions or template DBs.
- For full end-to-end, use `reqwest` against a real bound port with `TcpListener::bind("127.0.0.1:0")` to pick a free port.

## Database (sqlx)

Prefer the compile-time-checked macros over the runtime builder:

```rust
// Schema drift caught at `cargo build`, not at 3am in prod.
let user = sqlx::query_as!(
    User,
    "SELECT id, email, created_at FROM users WHERE id = $1",
    id,
)
.fetch_optional(&state.db)
.await?;
```

- `sqlx::query_as!` / `sqlx::query!` verify SQL against the real database schema at compile time. Requires `DATABASE_URL` in the environment or a checked-in `.sqlx/` offline query cache (`cargo sqlx prepare`).
- Use `.fetch_optional()` for "by id" lookups — returns `Option<T>`, maps cleanly to `AppError::NotFound`.
- `.fetch_all()` only when you've bounded the result set with `LIMIT`. No unbounded selects from request handlers.
- Transactions: `let mut tx = state.db.begin().await?;` → do work → `tx.commit().await?;`. Dropping without commit rolls back.
- Prefer `query_as!` + explicit struct over `FromRow` derive when the struct and SQL columns are 1:1; derive when you want reuse across multiple queries.

Ship `.sqlx/` in the repo so CI builds don't need a live database. Regenerate with `cargo sqlx prepare --workspace` when queries change.

## OpenAPI

`utoipa` generates OpenAPI from derive macros on handlers + types. `aide` is an alternative with better runtime integration. Either way: the schema is derived from code, not maintained separately.

```rust
#[derive(OpenApi)]
#[openapi(paths(get_user, create_user), components(schemas(UserResponse, CreateUser)))]
struct ApiDoc;
```

Serve the spec at `/openapi.json` and Swagger UI at `/docs` in non-prod environments.

## Common Traps

- Don't put an `Arc<Mutex<T>>` in `AppState` for things that should be behind a DB. Shared mutable state across requests is almost always a design smell.
- Don't use `tokio::sync::RwLock` where `arc-swap::ArcSwap` fits — config reloads, rarely-changing snapshots.
- Don't forget `with_state` at the end of router assembly. The compiler error is confusing (`method not found on Router<AppState>`).
- Don't bind to `0.0.0.0` in local dev unless you mean it. Use `127.0.0.1` by default; make the bind address configurable.
