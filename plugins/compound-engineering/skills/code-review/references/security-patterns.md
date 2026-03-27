# Security Detection Patterns

Grep-able patterns for the 11 security areas. Each entry: what to search for, why it's vulnerable, how to fix. Use during code review (step 4) and security audits.

## Deployment Entrypoints

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `debug=True`, `FLASK_DEBUG`, `DEBUG.*True` | Debug mode in production | `DEBUG = False`, env-conditional config |
| `--inspect`, `--inspect-brk` | Node inspector exposed in production | Remove from production startup scripts |
| `next dev`, `vite`, `uvicorn.*--reload` | Dev server in production | Use production servers (gunicorn, `vite build`, `next start`) |
| `x-powered-by` absent | Framework fingerprint exposed | `app.disable('x-powered-by')` (Express) |

## Config / Secrets

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `SECRET_KEY\s*=\s*['"]`, `API_KEY.*=`, `'sk-`, `AKIA`, `BEGIN PRIVATE` | Hardcoded secrets in source | Environment variables or secret managers |
| `NEXT_PUBLIC_.*SECRET`, `VITE_.*API_KEY` | Server secret leaked to client bundle | Only prefix public-safe values with `NEXT_PUBLIC_`/`VITE_` |
| `.env` tracked in git | Secrets committed to VCS | Add `.env`, `.env.local`, `.env.*.local` to `.gitignore` |
| `JSON.stringify.*user`, `__INITIAL_STATE__.*token` | Sensitive data serialized into SSR HTML | Sanitize server-side state before client hydration |

## Auth / AuthZ

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `?token=`, `?password=`, `?api_key=` | Secrets in URL query strings (logged, cached, referer-leaked) | Authorization headers, POST bodies, or HttpOnly cookies |
| `plaintext.*password`, `md5(`, `sha1(`, `hashlib.sha` | Weak password hashing | bcrypt, argon2id, or scrypt |
| `jwt.decode.*verify.*False`, `alg.*none` | JWT validation disabled or algorithm confusion | Enforce `verify_signature=True`, allowlist algorithms |
| Route without `Depends(get_current_user)` or auth middleware | Missing per-request authorization | Every state-changing endpoint must verify auth server-side |
| Frontend-only route guards (no server check) | Client-side auth bypass | Server-side authorization on every request; client guards are UX only |

## CSRF

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `@csrf_exempt`, `skip_csrf`, `disable.*csrf` | CSRF protection disabled on state-changing endpoint | Enable CSRF middleware, use tokens |
| Cookie-based auth without CSRF token | Session cookies sent automatically by browser | Add CSRF token to forms/AJAX, or use bearer token auth (no CSRF risk) |
| `SameSite` not set on session cookies | Cookies sent on cross-origin requests | `SameSite=Lax` (default) or `Strict` for session cookies |

## XSS

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `innerHTML =`, `insertAdjacentHTML`, `dangerouslySetInnerHTML`, `v-html=` | Untrusted HTML injected into DOM | `.textContent`, DOMPurify, or framework auto-escaping |
| `mark_safe(`, `Markup(`, `\|safe` in templates | Marking untrusted content as safe | Remove unsafe marking; auto-escape by default |
| `render_template_string(`, `Template(.*render`, `from_string(` | Server-side template injection (SSTI) | Static templates only; never render user input as template |
| `document.write(`, `eval(`, `new Function(`, `setTimeout(.*string` | String-to-code execution | Static imports, no dynamic code eval |
| `javascript:` in `href` or `src` attributes | Protocol-based XSS | Validate URLs, reject non-http/https schemes |

## Cache Security

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Cache-Control.*public` on auth-gated responses | Sensitive data cached by CDN/proxy | `Cache-Control: private, no-store` for user-specific data |
| `@cache_page` or `cache_control` on views with user data | Per-user content cached and served to other users | Cache only anonymous/public content, vary by auth |
| `__INITIAL_STATE__` with user data in SSR | User data leaked via cached HTML | Separate public shell from user-specific data fetching |

## File Handling

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `sendFile(.*req`, `send_file(.*request`, `os.path.join(.*request` | Path traversal via user-controlled path | Allowlist file IDs mapped to paths, `send_from_directory`, `safe_join` |
| File upload without size limit | Unrestricted upload = DoS | Set `MAX_CONTENT_LENGTH`, `express.json({ limit: '1mb' })` |
| Upload without content validation | Malicious file type bypass (rename .php to .jpg) | Validate via magic bytes (file signature), not extension |
| Serving uploaded files with `Content-Disposition: inline` | Uploaded HTML/JS executes in browser | Force `Content-Disposition: attachment`, serve from separate domain |
| `file.name` or `original_name` used for storage path | User-controlled filename = path traversal | Generate server-side UUID, store with randomized path |

## SQL / NoSQL Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `cursor.execute(f"`, `.query(f"`, `SELECT.*\+.*request` | String interpolation into SQL | Parameterized queries (`?`, `$1`, `%s`) |
| `Model.objects.raw(`, `.extra(`, `RawSQL(` | Django raw SQL with untrusted input | ORM methods or `params=` for raw queries |
| `find({.*request`, `$where`, `$ne`, `$gt` in MongoDB queries | NoSQL operator injection | Validate/sanitize query objects, reject `$`-prefixed keys in user input |
| `parseInt(req.query` without `radix` or type check | Type confusion leading to injection | Validate types explicitly, use Zod/validator at boundaries |

## SSRF

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `requests.get(.*request`, `fetch(.*request`, `http.Get(.*request` | Fetching user-provided URL without validation | Allowlist domains, block private IPs and metadata endpoints |
| `file://`, `gopher://`, `ftp://` in URL construction | Non-HTTP protocol SSRF | Whitelist `https:` scheme only |
| `169.254.169.254`, `metadata.google`, `100.100.100.200` | Cloud metadata endpoint access | Block metadata IP ranges in outbound requests |
| HTTP client without timeout | SSRF DoS via slow response | Set explicit timeouts: `timeout=5`, `Timeout: 10*time.Second` |

## Open Redirects

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `res.redirect(req.query`, `redirect(request.GET`, `window.location = params` | Redirect to untrusted URL | Validate against allowlist, allow only relative paths |
| `next=`, `return_to=`, `redirect=`, `url=`, `continue=` in params | Open redirect parameter without validation | `url_has_allowed_host_and_scheme` (Django), allowlist check |
| `location.href.*javascript:` | Protocol-based redirect attack | Reject non-http/https, validate with `new URL()` |

## CORS

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true` | Credentialed wildcard CORS = session theft | Explicit origin allowlist when using credentials |
| `CORS()` or `CORSMiddleware()` without explicit config | Default permissive CORS | Explicitly configure origins, methods, headers |
| Reflecting `Origin` header as `Access-Control-Allow-Origin` | Dynamic CORS that trusts any origin | Validate Origin against allowlist before reflecting |
| `Access-Control-Allow-Methods: *` | All HTTP methods exposed | Whitelist only needed methods |
