# Security Detection Patterns

Grep-able patterns for the common vulnerability classes. Each entry: what to search for, why it's vulnerable, how to fix. Use during code review (step 4) and security audits.

**Diff-anchored disabled-protection rule** (diff review only, `ia-code-review` step 4): flag only when the diff turns off a protection (CORS tightened then removed, debug enabled, `@csrf_exempt` added); never-present is architecture advice, not a finding. A full-repo security audit (`ia-security-sentinel`) has no diff to anchor to, so it flags a disabled protection on presence instead.

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

**Per-parameter secret redaction covers only the frame that declares the parameter.** The same secret sitting in an unannotated caller's parameter is still in the caller's frame, and a whole-trace scrubber hooked to one exception class is not equivalent: changing the thrown type is then not redaction-neutral. Verify by triggering through a wrapper whose own parameter carries no annotation, and assert the secret is absent from the whole trace.

## Auth / AuthZ

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `?token=`, `?password=`, `?api_key=` | Secrets in URL query strings (logged, cached, referer-leaked) | Authorization headers, POST bodies, or HttpOnly cookies |
| `plaintext.*password`, `md5(`, `sha1(`, `hashlib.sha` | Weak password hashing | bcrypt, argon2id, or scrypt |
| `jwt.decode.*verify.*False`, `alg.*none` | JWT validation disabled or algorithm confusion | Enforce `verify_signature=True`, allowlist algorithms |
| `kid`, `jku`, `x5u`, embedded `jwk` selecting the key | Attacker-controlled until pinned; key-confusion accepts an RS256 public key as an HS256 secret | Resolve `kid` against a fixed JWKS only; never fetch `jku`/`x5u` or import `jwk` (version preconditions: Version-Gated False Positives below) |
| Route without `Depends(get_current_user)` or auth middleware | Missing per-request authorization | Every state-changing endpoint must verify auth server-side |
| Frontend-only route guards (no server check) | Client-side auth bypass | Server-side authorization on every request; client guards are UX only |
| `===`, `!=`, `==`, `.equals(` comparing a bearer token, API key, webhook signature, or reset token | Byte-by-byte timing leak from early-exit comparison (CWE-208) | Compare length first (length is not secret), then `crypto.timingSafeEqual` (Node), `hash_equals` (PHP), `hmac.compare_digest` (Python), `subtle::ConstantTimeEq` (Rust). Guard the absent-header case before comparing |
| `fill($request->all())`, `$guarded = []`, spreading `req.body` into a write | Mass assignment as an authz bug: body maps onto owner/role/tenant/price | Explicit `$fillable`/DTO allowlist; never `fill()`/spread a raw body onto a privileged model |
| List/index handler scopes by owner; sibling export/share/detail handler omits the check | IDOR/BOLA: one route's guard doesn't cover its siblings | Diff every handler for the resource; each needs its own ownership check |
| Unknown role reaching `allow`; `Gate::before` returning `true`; authz middleware after the route, or an in-check exception hitting `next()` | Fail-open authz: default-allow or ordering grants access | Default denies; `Gate::before` reserved for a documented bypass; middleware before the route, reject not `next()` |

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
| A helper containing both `textContent =` and `.innerHTML` (the round-trip escaper) | Text-node serialization escapes only `&`, `<`, `>` and U+00A0; quotes pass through, so the result still breaks out of `attr="${escaped}"` | Escape `"` and `'` explicitly, or set the attribute via `setAttribute`/`dataset` instead of building HTML |
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
| A `..`-component check that splits the path on `/` only (`split('/')`, `explode('/', ...)`, `path.split('/')`) | A `..\` component passes the filter and is honored by any consumer that treats `\` as a separator: a Windows filesystem API, a Windows-hosted CI runner, or a later normalization step | Normalize separators (`\` to `/`) *before* splitting and checking components; a filter written for `/`-only input is not a traversal guard |
| Delete/move/overwrite on a job-payload or sibling-service path, guarded only by shape (absolute, N dirs deep) | Shape isn't authorization: `startsWith(base)` matches `/base2` | Require: allowlisted root (post-symlink), one level below it, ownership evidence read first; log and stop on refusal, never a broader default |
| File upload without size limit | Unrestricted upload = DoS | Set `MAX_CONTENT_LENGTH`, `express.json({ limit: '1mb' })` |
| Upload without content validation | Malicious file type bypass (rename .php to .jpg) | Validate via magic bytes (file signature), not extension |
| Serving uploaded files with `Content-Disposition: inline` | Uploaded HTML/JS executes in browser | Force `Content-Disposition: attachment`, serve from separate domain |
| `file.name` or `original_name` used for storage path | User-controlled filename = path traversal | Generate server-side UUID, store with randomized path |
| A no-follow open or `lstat` guard on a path whose parent directories come from untrusted content | Both apply to the last component only: one symlinked parent redirects every fixed-name file below it, and `exists()` follows links, so a dangling symlink reads as absent | Validate the untrusted root before any leaf access, through one shared helper; use link-aware metadata rather than `exists()`; generate temp names freshly |
| Read-whole-file under an untrusted root, guarded only against symlink writes | A symlink to an endless character device returns valid UTF-8 forever and the process exhausts memory | Require a regular file via `fstat` on the open descriptor, and cap the read by size |
| `stat`/`lstat` on a path, then `open`/`unlink`/`chmod` on the same path | Link-following race (CWE-59/367): the path can be swapped for a symlink between the check and the operation, so a check on the path never covers the operation | Open with `O_NOFOLLOW`, then verify identity via `fstat` on the *descriptor* against a fresh `lstat` of the path (compare `dev`+`ino`), and reject `nlink != 1` to catch hardlink aliasing. A pre-open `lstat` check alone is still exploitable |
| `tarfile` `extractall(`/`extract(` without `filter=`; a loop over `ZipFile.infolist()`, `ZipArchive::getNameIndex()`, `adm-zip`, or `yauzl` entries that builds `os.path.join(dest, entry.name)` or `dest + name` | Zip-slip: an entry name that is absolute, contains `..`, or uses `\` as a separator writes outside the destination; a symlink or hardlink entry extracted first lets a later entry write *through* it | Resolve each entry's final path and require it under `realpath(dest)` plus a separator (component boundary, not string prefix); reject link entries or check their targets the same way before any later write. Python: pass `filter="data"` (added in 3.12, backported to some older releases as a security fix, default only from 3.14). Cap total expanded size and entry count, not only per-file size |

## SQL / NoSQL Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `cursor.execute(f"`, `.query(f"`, `SELECT.*\+.*request` | String interpolation into SQL | Parameterized queries (`?`, `$1`, `%s`) |
| `Model.objects.raw(`, `.extra(`, `RawSQL(` | Django raw SQL with untrusted input | ORM methods or `params=` for raw queries |
| `find({.*request`, `$where`, `$ne`, `$gt` in MongoDB queries | NoSQL operator injection | Validate/sanitize query objects, reject `$`-prefixed keys in user input |
| `parseInt(req.query` without `radix` or type check | Type confusion leading to injection | Validate types explicitly, use Zod/validator at boundaries |

## Command / Argument Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| PHP `exec(`, `system(`, `shell_exec(`, `passthru(`, backticks, `popen(`, `proc_open(` with a string command; Python `os.system(`, `subprocess.*(..., shell=True)`; Node `child_process.exec(`/`execSync(`, `spawn(..., { shell: true })` | A request-derived value inside a shell command string: `;`, `&&`, `$(...)`, backticks, and newlines run attacker commands | Pass an argv array with no shell: `proc_open([...])` (PHP 7.4+), `subprocess.run([...])` without `shell=True`, `execFile`/`spawn` with an argument array. When a shell string is unavoidable, wrap each value in `escapeshellarg()`; `escapeshellcmd()` on a whole command still lets the attacker add arguments |
| An argv element or `escapeshellarg()`-quoted value taken from untrusted input (request, uploaded file, repository content, another user) and passed to `git`, `ssh`, `curl`, `tar`, `rsync`, `find`, or similar | Option injection: argv form and quoting stop shell parsing, not option parsing, so a value starting with `-` becomes a flag (`--upload-pack=`, `-oProxyCommand=`, `-K`/`-o`, `--checkpoint-action=`, `-e`, `-exec`) that runs a command or writes a file | Reject a leading `-`, and place `--` before the untrusted operand for tools that honor it; a `--` after an operand does not protect that operand. `find` is an exception: its `--` ends only the leading options (`-H`, `-L`, `-P`, `-D`, `-O`), so a later `-exec` is still an expression; reject a leading `-`, prefix relative paths with `./`, and never build the expression from input. For git revision operands, see the next row |
| `git log "$ref"`, `git log "$ref" --`, `git checkout "$branch"`, `git clone "$url"` with an input-derived ref or URL | In git, a ref placed before `--` is read as an option when it starts with `-` (`--output=` writes a file); `--` does stop option parsing, but it turns every later argument into a pathspec, so `git log -- "$ref"` is not injectable yet cannot carry a revision; `<transport>::` URLs invoke a remote helper, and `file` transport reads local repositories when the user runs the command | Put `--end-of-options` (git 2.24+) before revision operands; allowlist `https://`/`ssh://` for input-supplied clone and fetch URLs and reject a leading `-` |

## SSRF

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `requests.get(.*request`, `fetch(.*request`, `http.Get(.*request` | Fetching user-provided URL without validation | Allowlist domains, block private IPs and metadata endpoints |
| `file://`, `gopher://`, `ftp://` in URL construction | Non-HTTP protocol SSRF | Whitelist `https:` scheme only |
| `169.254.169.254`, `metadata.google`, `100.100.100.200` | Cloud metadata endpoint access | Block metadata IP ranges in outbound requests |
| HTTP client without timeout | SSRF DoS via slow response | Set explicit timeouts: `timeout=5`, `Timeout: 10*time.Second` |
| A credentialed client following redirects (`allow_redirects`, `redirect: 'follow'`, `maxRedirects`), or a token sent to a URL read from a response (`Location`, `Link: rel=next`, a pagination `next` field, a `WWW-Authenticate` realm or token endpoint) | The credential leaves its origin. On a redirect, Python `requests` strips `Authorization` (keeping it on a same-host http-to-https hop) and drops a manually set `Cookie` header, re-sending only jar cookies that match the new domain; undici `fetch` and Guzzle strip `Authorization` and `Cookie` on a cross-origin hop (Guzzle before 7.4.5 missed the HTTPS-downgrade and port-change cases); `follow-redirects` (axios in Node) keeps them when the new host is a subdomain. Custom credential headers (`X-Api-Key`, `PRIVATE-TOKEN`, `X-Auth-Token`) are forwarded by all of these | Bind each credential to an origin allowlist checked on every hop, or disable auto-redirect and re-authorize per request; never attach a token to a response-supplied URL without the same origin check |

## Open Redirects

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `res.redirect(req.query`, `redirect(request.GET`, `window.location = params` | Redirect to untrusted URL | Validate against allowlist, allow only relative paths |
| `next=`, `return_to=`, `redirect=`, `url=`, `continue=` in params | Open redirect parameter without validation | `url_has_allowed_host_and_scheme` (Django), allowlist check |
| `location.href.*javascript:` | Protocol-based redirect attack | Reject non-http/https, validate with `new URL()` |

## CRLF / Header Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `setHeader(`, `header(`, `Response.headers[...] =`, `add_header` with a request-derived or externally-sourced value | `\r`/`\n` in the value splits the header block, injecting extra headers or a whole second response (response splitting) | Reject any byte below `0x20` (except tab) and `0x7f` *before* trimming whitespace; reject multi-line values outright. Prefer the framework's header API over string-built raw responses |
| `Location:`, `Set-Cookie:`, `Content-Disposition: ...filename=` built by interpolation | Cookie or redirect forged via a smuggled newline; `filename=` also carries a quote-escape | Allowlist or percent-encode the interpolated part; for `filename` use RFC 5987 `filename*=UTF-8''...` |
| A secret or config value fetched at runtime (env, file, `credential_process`-style subprocess) used verbatim as an `Authorization` header | An opaque header-validation error at best; a control byte in the fetched value is a header-injection primitive | Validate the fetched value for control bytes at the point it is read, not at the point it is sent |

## CORS

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true` | Browsers block credentialed response access with a wildcard origin; this combination alone does not establish session theft | Use an explicit origin allowlist for intended credentialed clients; test actual response headers and browser access |
| `CORS()` or `CORSMiddleware()` without explicit config | Defaults depend on the package and version; Starlette's CORSMiddleware defaults are restrictive | Inspect the installed middleware and effective configuration before reporting exposure; configure the origins, methods, and headers the application needs |
| Reflecting `Origin` header as `Access-Control-Allow-Origin` | Dynamic CORS that trusts any origin | Validate Origin against allowlist before reflecting |
| `Access-Control-Allow-Methods: *` | All HTTP methods exposed | Whitelist only needed methods |

## Insecure Deserialization / XXE

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `pickle.loads(`, `marshal.loads(`, `yaml.load(` without `Loader=SafeLoader` | Arbitrary object/code execution on untrusted input | `json.loads`, `yaml.safe_load`, or a signed/allowlisted schema |
| `unserialize($` on user input (PHP) | Object injection / POP-chain gadget execution | `json_decode`, or `unserialize($x, ['allowed_classes' => false])` |
| `etree.parse(`/`lxml` without `resolve_entities=False`; `DocumentBuilderFactory` without `disallow-doctype-decl` | XXE: external entity expansion reads files or triggers SSRF | Disable DTD/external entities on the parser |

## Weak Randomness / TLS Verification

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Math.random(`, `random.random(`, `mt_rand(` for tokens/secrets/IDs | Predictable value used as a security control | `crypto.randomBytes`, `secrets.token_urlsafe`, `random_bytes` |
| `verify=False` (requests), `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `InsecureSkipVerify: true` | TLS certificate validation disabled (MITM) | Remove the flag; trust/pin the proper CA in the client |
| ECB mode, static/reused IV or nonce, home-rolled crypto, MD5/SHA1 for integrity | Deterministic ciphertext, reused nonce, forgeable integrity checks | AES-GCM/ChaCha20-Poly1305 with a fresh nonce, audited libraries, HMAC-SHA256+ |
| `sha256`/`hash_file(`/`hashlib`/signature or HMAC verify on a downloaded, cached, or uploaded artifact (installers, self-updaters, plugin or dependency fetchers) | Integrity check fails open: a missing or malformed digest counts as a pass, a mismatch is only logged or its return value is ignored, a mismatch falls back to a mirror or backend that skips verification, or a cache hit is used without re-verifying | A missing digest is a failure; route every acquisition path, cache reads included, through one verify-then-use helper that refuses the artifact on mismatch. A valid digest proves byte identity only, so archive-extraction checks (File Handling) still apply |

## Version-Gated False Positives

| Pattern | Only a finding when |
|---------|---------------------|
| PHP `assert("...")` string-eval; `preg_replace(...)` with `/e` | PHP < 8.0 (assert removed); PHP < 7.0 (`/e` removed) |
| `yaml.load(...)` without `Loader=SafeLoader` | PyYAML < 5.4 (`FullLoader` exploitable before); use `safe_load` regardless |
| XXE via default entity expansion | libxml2 < 2.9.0 (disabled by default since); PHP `libxml_disable_entity_loader()` is dead code from 8.0 |
| `jsonwebtoken`/`PyJWT` key-confusion via `kid`/`jku`/`x5u`/`jwk` | `jsonwebtoken` < 9.0.0 (CVE-2022-23540/23539): finding only when all of: `jwt.verify` called with no explicit `algorithms` option and a falsy/empty verification key, or an RSA key accepted for an HS-family algorithm. `PyJWT` < 2.4.0 (CVE-2022-29217): finding only when all of: the app allows both asymmetric and HMAC algorithms and the supplied public key is in a PEM/SSH format the pre-2.4.0 blocklist missed |
| Next.js Server Actions SSRF | Next.js < 14.1.1, CVE-2024-34351: finding only when all of: self-hosted (not Vercel), the `Host` header reaching the app is attacker-controllable, Server Actions are in use, and a Server Action redirects to a relative path |
