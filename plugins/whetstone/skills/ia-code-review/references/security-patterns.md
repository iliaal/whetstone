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

**Check exclusion against the serializer used by the leaking sink.** Dataclass `field(repr=False)` hides a field from the generated representation, but `asdict()` still includes it. Pydantic `Field(repr=False)` does not exclude a field from `model_dump()`; export exclusion is a separate setting. TypeScript `private` does not hide a property at runtime. A `toJSON()` redactor affects `JSON.stringify()`, but Node's `util.inspect()` uses a different path and options. Trace a production credential into the actual output before reporting exposure; a secret-shaped fixture alone does not establish a leak. Run the regression through the sink's serializer and options, including nested objects, rather than testing only the redactor in isolation.

**Per-parameter secret redaction covers only the frame that declares the parameter.** The same secret sitting in an unannotated caller's parameter is still in the caller's frame, and a whole-trace scrubber hooked to one exception class is not equivalent: changing the thrown type is then not redaction-neutral. Verify by triggering through a wrapper whose own parameter carries no annotation, and assert the secret is absent from the whole trace.

## Auth / AuthZ

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `?token=`, `?password=`, `?api_key=` | Secrets in URL query strings (logged, cached, referer-leaked) | Authorization headers, POST bodies, or HttpOnly cookies |
| `plaintext.*password`, `md5(`, `sha1(`, `hashlib.sha` | Weak password hashing | bcrypt, argon2id, or scrypt |
| `jwt.decode.*verify.*False`, `alg.*none`, `jwt.verify` without required claims | JWT verification disabled, algorithm confusion, or missing expiry/subject accepted; PyJWT and jsonwebtoken check expiry only when `exp` exists | Verify signatures; allowlist algorithms; require and validate `exp` and `sub` for identity tokens (PyJWT: `options={"require": ["exp", "sub"]}`) |
| OAuth/OIDC callback reading `state`, PKCE verifier, or `nonce` from mutable session state | Replay or concurrent callbacks reuse a flow; another login overwrites its nonce | With state, match a non-empty string to the session; otherwise verify transaction-specific PKCE/nonce bound to the browser session (PKCE requires server support). Capture and consume the flow record before exchange: before any `await` in memory, atomically (`GETDEL`, conditional `DELETE ... RETURNING`) in a shared store. Match any requested ID-token nonce to the captured value before token use; restart after exchange failure. Exact-match allowed `redirect_uri` values, except native-app loopback ports |
| Account-switch callback clearing/rebinding a session before validating its CSRF binding | Forced-navigation logout or identity switch; error branches retain the previous identity when the switch promises to end it | Validate and consume the flow before changing identity. Exercise denied/cancelled/error branches against the promised session lifecycle |
| `kid`, `jku`, `x5u`, embedded `jwk` selecting the key | Attacker-controlled until pinned; key-confusion accepts an RS256 public key as an HS256 secret | Resolve `kid` against a fixed JWKS only; never fetch `jku`/`x5u` or import `jwk` (version preconditions: Version-Gated False Positives below) |
| Route without `Depends(get_current_user)` or auth middleware; ownership granted before a role downgrade | Missing per-request authorization; stale grants permit later reads | Check current role and resource access server-side on every protected read or mutation |
| Frontend-only route guards (no server check) | Client-side auth bypass | Server-side authorization on every request; client guards are UX only |
| `===`, `!=`, `==`, `.equals(` comparing a bearer token, API key, webhook signature, or reset token | Byte-by-byte timing leak from early-exit comparison (CWE-208) | Compare length first (length is not secret), then `crypto.timingSafeEqual` (Node), `hash_equals` (PHP), `hmac.compare_digest` (Python), `subtle::ConstantTimeEq` (Rust). Guard the absent-header case before comparing |
| `fill($request->all())`, `$guarded = []`, spreading `req.body` into a write | Mass assignment as an authz bug: body maps onto owner/role/tenant/price | Explicit `$fillable`/DTO allowlist; never `fill()`/spread a raw body onto a privileged model |
| List/index handler scopes by owner; sibling export/share/detail handler omits the check | IDOR/BOLA: one route's guard doesn't cover its siblings | Diff every handler for the resource; each needs its own ownership check |
| Primary query scoped by tenant/owner/consent; a follow-up `whereIn('id', $ids)` loads related rows by id alone | Scope does not carry to the secondary by-id load: a stale or malformed foreign id surfaces another owner's row under this parent | Scope the secondary load by the same owner key, or reject a loaded row whose owner differs from the parent's; rate severity by who can write the foreign id |
| Unknown role reaching `allow`; `Gate::before` returning `true`; authz middleware after the route, or an in-check exception hitting `next()` | Fail-open authz: default-allow or ordering grants access | Default denies; `Gate::before` reserved for a documented bypass; middleware before the route, reject not `next()` |
| Shared 403/404/500 renderer loading names or counts outside the authz path | Denial page discloses data the blocked role cannot read | Apply the same access scope to error context, or render public-only context |
| `trust proxy: true`, `TrustProxies('*')`, `forwarded_allow_ips='*'`, direct `X-Forwarded-*` reads | Spoofed IP/scheme/host controls an IP gate, rate limit, HTTPS check, or generated URL | Confirm deployment topology before assigning severity. Trust known proxy subnets or a fixed hop count with no shorter ingress path; require the last trusted proxy to strip/overwrite client-supplied forwarded headers |

## CSRF

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `@csrf_exempt`, `skip_csrf`, `disable.*csrf` | CSRF protection disabled on state-changing endpoint | Enable CSRF middleware, use tokens |
| Cookie-based auth without CSRF token | Session cookies sent automatically by browser | Add CSRF token to forms/AJAX, or use bearer token auth (no CSRF risk) |
| `SameSite` not set on session cookies | Cookies sent on cross-origin requests | `SameSite=Lax` (default) or `Strict` for session cookies |
| Localhost-bound server using `Host`, `Origin`, or `Sec-Fetch-Site` checks as authentication | Different localhost ports on the same scheme are same-site; non-browser local processes choose any `Host`; server-side clients following a `307` to `127.0.0.1` can replay the request into the local server | Require a random per-install token stored in a `0600` file, sent only to the exact trusted origin in an `Authorization: Bearer` header. Cookies lack port isolation ([RFC 6265 §8.5](https://www.rfc-editor.org/rfc/rfc6265.html#section-8.5)). `Host`, `Origin`, and `Sec-Fetch-Site` checks only supplement authentication |

For browser WebSockets authenticated by automatically sent cookies, check authentication and an explicit `Origin` allowlist at the handshake. HTTP CORS middleware does not establish either check for WebSocket messages. Demonstrate a hostile page's actual protected read or mutation before reporting cross-site exposure. `Origin` identifies browser provenance, not user identity: non-browser clients can forge it. Assess a missing header against the supported clients and authentication policy rather than treating every absent `Origin` as a vulnerability. See [RFC 6455 origin considerations](https://www.rfc-editor.org/rfc/rfc6455.html#section-10.2).

## XSS

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `innerHTML =`, `insertAdjacentHTML`, `dangerouslySetInnerHTML`, `v-html=` | Untrusted HTML injected into DOM | `.textContent`, DOMPurify, or framework auto-escaping |
| A helper containing both `textContent =` and `.innerHTML` (the round-trip escaper) | Text-node serialization escapes only `&`, `<`, `>` and U+00A0; quotes pass through, so the result still breaks out of `attr="${escaped}"` | Escape `"` and `'` explicitly, or set the attribute via `setAttribute`/`dataset` instead of building HTML |
| `mark_safe(`, `Markup(`, `\|safe` in templates | Marking untrusted content as safe | Remove unsafe marking; auto-escape by default |
| Jinja `\|tojson` inside a double-quoted HTML attribute | Attacker-controlled JSON retains double quotes in a safe-marked value, allowing attribute breakout; auto-escape and ordinary `escape` trust that value | Use a single-quoted attribute or apply `\|forceescape` after `\|tojson`; exercise the actual attribute context. See [Jinja's `tojson` contract](https://jinja.palletsprojects.com/en/stable/templates/#jinja-filters.tojson) |
| `render_template_string(`, `Template(.*render`, `from_string(` | Server-side template injection (SSTI) | Static templates only; never render user input as template |
| `document.write(`, `eval(`, `new Function(`, `setTimeout(.*string` | String-to-code execution | Static imports, no dynamic code eval |
| `javascript:` in `href` or `src` attributes | Protocol-based XSS | Validate URLs, reject non-http/https schemes |
| `JSON.stringify`, `json.dumps`, or `json_encode` embedded in a hand-built `<script>` / JSON island | Raw `</script>` terminates the element even inside JSON; HTML parsing precedes JS parsing | Escape `<` as `\u003c` in serialized JSON (PHP: `JSON_HEX_TAG`), or use `Js::from`, Django `json_script`, or Jinja `tojson` for the matching context. Verify existing framework hydration escaping before reporting |

## Cache Security

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Cache-Control.*public` on auth-gated responses | Sensitive data cached by CDN/proxy | `Cache-Control: private, no-store` for user-specific data |
| `@cache_page` or `cache_control` on views with user data | Per-user content cached and served to other users | Cache only anonymous/public content, vary by auth |
| `__INITIAL_STATE__` with user data in SSR | User data leaked via cached HTML | Separate public shell from user-specific data fetching |

## File Handling

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `sendFile(`, `send_file(`, `FileResponse(` with input-derived paths | Traversal when input escapes the intended root; `join`/`normalize`/`resolve` alone do not enforce containment | Map authorized file IDs to paths. Fixed-root Express `sendFile` and Flask `send_from_directory`/`safe_join` constrain path traversal; standard Laravel `Storage` keys are disk-relative. Check custom adapters and attacker-controlled symlinks separately |
| A `..`-component check that splits the path on `/` only (`split('/')`, `explode('/', ...)`, `path.split('/')`) | A `..\` component passes the filter and is honored by any consumer that treats `\` as a separator: a Windows filesystem API, a Windows-hosted CI runner, or a later normalization step | Normalize separators (`\` to `/`) *before* splitting and checking components; a filter written for `/`-only input is not a traversal guard |
| Delete/move/overwrite on a job-payload or sibling-service path, guarded only by shape (absolute, N dirs deep) | Shape isn't authorization: `startsWith(base)` matches `/base2` | Require: allowlisted root (post-symlink), one level below it, ownership evidence read first; log and stop on refusal, never a broader default |
| File upload without size limit | Unrestricted upload = DoS | Set limits in the actual upload parser: Flask `MAX_CONTENT_LENGTH`; Multer `limits.fileSize`, `limits.files`, and `limits.parts`, plus `limits.fieldNestingDepth` (multer 2.2.0+) and `limits.fieldArrayIndexLimit` (multer 2.3.0+), both defaulting to `Infinity`; a field name like `a[4294967294]` builds a sparse array whose length the application pays for when it iterates or serializes `req.body`, and no option bounds it before 2.3.0. Use `express.json({ limit: '1mb' })` only for JSON bodies, not multipart uploads |
| Upload without content validation | Malicious file type bypass (rename .php to .jpg) | Validate via magic bytes (file signature), not extension |
| Serving uploaded files with `Content-Disposition: inline` | Uploaded HTML/JS executes in browser | Force `Content-Disposition: attachment`, serve from separate domain |
| `file.name` or `original_name` used for storage path | User-controlled filename = path traversal | Generate server-side UUID, store with randomized path |
| A no-follow open or `lstat` guard on a path whose parent directories come from untrusted content | Both apply to the last component only: one symlinked parent redirects every fixed-name file below it, and `exists()` follows links, so a dangling symlink reads as absent | Validate the untrusted root before any leaf access, through one shared helper; use link-aware metadata rather than `exists()`; generate temp names freshly |
| Read-whole-file under an untrusted root, guarded only against symlink writes | A symlink to an endless character device returns valid UTF-8 forever and the process exhausts memory | Require a regular file via `fstat` on the open descriptor, and cap the read by size |
| `stat`/`lstat` on a path, then `open`/`unlink`/`chmod` on the same path | TOCTOU (CWE-59/367): `open`/`chmod` can follow a replacement symlink; `unlink` removes the final symlink itself, but can remove a replacement entry or resolve a swapped parent | Open without truncation through trusted parents with `O_NOFOLLOW`; validate the opened file with `fstat`, reject `nlink != 1` where hardlink aliases are forbidden, and use that descriptor for I/O and `fchmod(fd)`. For deletion, use `unlinkat(dirfd, leaf, 0)` with a held trusted parent-directory descriptor and a single leaf name; prevent untrusted replacement of that entry when deleting the validated object is required. Comparing `dev`+`ino` with fresh `lstat` detects mismatches but does not make a later pathname operation atomic |
| `tarfile` `extractall(`/`extract(` without `filter=`; a loop over `ZipFile.infolist()`, `ZipArchive::getNameIndex()`, `adm-zip`, or `yauzl` entries that builds `os.path.join(dest, entry.name)` or `dest + name` | Zip-slip: an entry name that is absolute, contains `..`, or uses `\` as a separator writes outside the destination; a symlink or hardlink entry extracted first lets a later entry write *through* it | Resolve each entry's final path and require it under `realpath(dest)` plus a separator (component boundary, not string prefix); reject link entries or check their targets the same way before any later write. Python: pass `filter="data"` (added in 3.12, backported to some older releases as a security fix, default only from 3.14). Cap total expanded size and entry count, not only per-file size |

## SQL / NoSQL Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `cursor.execute(f"`, `.query(f"`, `SELECT.*\+.*request` | String interpolation into SQL | Parameterized queries (`?`, `$1`, `%s`) |
| `Model.objects.raw(`, `.extra(`, `RawSQL(` | Django raw SQL with untrusted input | ORM methods or `params=` for raw queries |
| `find({.*request`, `$where`, `$ne`, `$gt` in MongoDB queries | NoSQL operator injection | Validate/sanitize query objects, reject `$`-prefixed keys in user input |
| `parseInt(req.query` without `radix` or type check | Type confusion leading to injection | Validate types explicitly, use Zod/validator at boundaries |

## Prototype Pollution (JS/TS)

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `deepMerge`, `_.merge`/`_.set`/`_.defaultsDeep`, `obj[k1][k2] = v` over request-derived keys | A recursive walker follows `__proto__` or `constructor.prototype`; report with a reachable inherited-property gadget (role check, process or template options), not the API name alone | Reject `__proto__`, `constructor`, and `prototype` at every depth, or use `Map`/null-prototype dictionaries throughout the traversal. `JSON.parse` alone creates an own key; unsafe later traversal creates the pollution |

## Command / Argument Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| PHP `exec(`, `system(`, `shell_exec(`, `passthru(`, backticks, `popen(`, `proc_open(` with a string command; Python `os.system(`, `subprocess.*(..., shell=True)`; Node `child_process.exec(`/`execSync(`, `spawn(..., { shell: true })` | A request-derived value inside a shell command string: `;`, `&&`, `$(...)`, backticks, and newlines run attacker commands | Pass an argv array with no shell: `proc_open([...])` (PHP 7.4+), `subprocess.run([...])` without `shell=True`, `execFile`/`spawn` with an argument array. When a shell string is unavoidable, wrap each value in `escapeshellarg()`; `escapeshellcmd()` on a whole command still lets the attacker add arguments |
| An argv element or `escapeshellarg()`-quoted value taken from untrusted input (request, uploaded file, repository content, another user) and passed to `git`, `ssh`, `curl`, `tar`, `rsync`, `find`, or similar | Option injection: argv form and quoting stop shell parsing, not option parsing, so a value starting with `-` becomes a flag (`--upload-pack=`, `-oProxyCommand=`, `-K`/`-o`, `--checkpoint-action=`, `-e`, `-exec`) that runs a command or writes a file | Reject a leading `-`, and place `--` before the untrusted operand for tools that honor it; a `--` after an operand does not protect that operand. `find` is an exception: its `--` ends only the leading options (`-H`, `-L`, `-P`, `-D`, `-O`), so a later `-exec` is still an expression; reject a leading `-`, prefix relative paths with `./`, and never build the expression from input. For git revision operands, see the next row |
| `git log "$ref"`, `git log "$ref" --`, `git checkout "$branch"`, `git clone "$url"` with an input-derived ref or URL | In git, a ref placed before `--` is read as an option when it starts with `-` (`--output=` writes a file); `--` does stop option parsing, but it turns every later argument into a pathspec, so `git log -- "$ref"` is not injectable yet cannot carry a revision; `<transport>::` URLs invoke a remote helper, and `file` transport reads local repositories when the user runs the command | Put `--end-of-options` (git 2.24+) before revision operands; allowlist `https://`/`ssh://` for input-supplied clone and fetch URLs and reject a leading `-` |

## Hidden Code in Comment-Only Hunks

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| A hunk that appears to touch only comments or whitespace, especially in third-party, vendored, or agent-authored changes; `grep -nP '[\x{2028}\x{2029}\x{202A}-\x{202E}\x{2066}-\x{2069}]'` (UTF-8 locale) | JavaScript ends a `//` comment at U+2028 or U+2029, so text after either runs as code. A C/C++ `//` comment ending in `\` (or the trigraph `??/` where trigraphs are enabled) splices the next line into the comment. Adding or removing a trailing `\` changes which lines join. Bidi controls (U+202A to U+202E, U+2066 to U+2069) make rendered source differ from what the compiler reads (Trojan Source, CVE-2021-42574) | Render invisible and line-terminator code points as escapes and re-read the hunk; treat it as code, never as "comment only" |

## SSRF

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `requests.get(.*request`, `fetch(.*request`, `file_get_contents($url)` | URL checks bypassed by DNS rebinding or redirects | Allowlist parsed scheme/host; reject URLs containing userinfo. Check every resolved address and pin the connection to a validated IP via lookup/connect hooks or an egress proxy, preserving Host, TLS SNI, and hostname verification. Disable redirects or repeat all checks per hop |
| `file://`, `gopher://`, `ftp://` in URL construction | Alternate-scheme access only when the actual client supports it | Allowlist schemes before I/O. `urllib.request`'s default opener includes redirects, FTP, and file handlers; Node core `http(s).request` supports neither file/gopher nor automatic redirects |
| `169.254.169.254`, `metadata.google`, `100.100.100.200` | Cloud metadata endpoint access | Block metadata IP ranges in outbound requests |
| String-prefix IP filters, single-address DNS checks | Decimal/octal IPv4, `0.0.0.0`, `[::1]`, or IPv4-mapped `::ffff:127.0.0.1` bypass the filter | Canonicalize with the client's URL parser and an IP parser; reject ambiguous forms. Block loopback, private, link-local, unspecified, and metadata destinations across IPv4/IPv6, including mapped addresses |
| HTTP client without timeout | SSRF DoS via slow response | Set explicit timeouts, e.g. `timeout=5` (requests) |
| Unencoded identifier concatenated into a fixed upstream URL path | Secondary-context path traversal reaches another endpoint on the same host with server credentials; not host-control SSRF | Allowlist identifier syntax, or encode each segment and reject `.`/`..`; encoding alone leaves bare dots intact. Verify the upstream's decoding behavior |
| A credentialed client following redirects (`allow_redirects`, `redirect: 'follow'`, `maxRedirects`), or a token sent to a URL read from a response (`Location`, `Link: rel=next`, a pagination `next` field, a `WWW-Authenticate` realm or token endpoint) | The credential leaves its origin. On a redirect, Python `requests` strips `Authorization` (keeping it on a same-host http-to-https hop) and drops a manually set `Cookie` header, re-sending only jar cookies that match the new domain; undici `fetch` and Guzzle strip `Authorization` and `Cookie` on a cross-origin hop (Guzzle before 7.4.5 missed the HTTPS-downgrade and port-change cases); `follow-redirects` (axios in Node) keeps them when the new host is a subdomain. Custom credential headers (`X-Api-Key`, `PRIVATE-TOKEN`, `X-Auth-Token`) are forwarded by all of these | Bind each credential to an origin allowlist checked on every hop, or disable auto-redirect and re-authorize per request; never attach a token to a response-supplied URL without the same origin check |

Check effective client defaults: requests follows redirects except for HEAD; fetch defaults to `redirect: 'follow'`; Guzzle's default redirect middleware allows 5 hops (`sendRequest()` does not follow). PHP `allow_url_fopen` defaults on, enabling HTTP URLs in `file_get_contents`. Client wrappers can override these defaults.

## Open Redirects

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `res.redirect(req.query`, `window.location = params`, `startsWith('/')`, `!includes('//')`, `/^https?:/` URL guards | Raw checks disagree with browser parsing: `/\host`, `//host`, or embedded tabs/newlines change destination/scheme | Parse with `new URL(value, trustedBase)` or a framework helper; require an allowed protocol and origin, then redirect to the parsed value. Same-origin redirects require exact origin equality |
| `next=`, `return_to=`, `redirect=`, `url=`, `continue=` in params | Open redirect parameter without validation | `url_has_allowed_host_and_scheme` (Django), allowlist check |
| `location.href.*javascript:` | Protocol-based redirect attack | Apply the protocol/origin checks above after parsing; a successful parse alone is not validation |

## CRLF / Header Injection

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `setHeader(`, `header(`, `Response.headers[...] =`, `add_header` with a request-derived or externally-sourced value | `\r`/`\n` in the value splits the header block, injecting extra headers or a whole second response (response splitting) | Reject any byte below `0x20` (except tab) and `0x7f` *before* trimming whitespace; reject multi-line values outright. Prefer the framework's header API over string-built raw responses |
| `Location:`, `Set-Cookie:`, `Content-Disposition: ...filename=` built by interpolation | Cookie or redirect forged via a smuggled newline; `filename=` also carries a quote-escape | Allowlist or percent-encode the interpolated part; for `filename` use RFC 5987 `filename*=UTF-8''...` |
| A secret or config value fetched at runtime (env, file, `credential_process`-style subprocess) used verbatim as an `Authorization` header | An opaque header-validation error at best; a control byte in the fetched value is a header-injection primitive | Validate the fetched value for control bytes at the point it is read, not at the point it is sent |
| `re.match(r"^...$"`, `re.search(r"^...$"`, `preg_match('/^...$/'` without the `D` modifier, used as an allowlist validator | In Python `re` and PHP PCRE, `$` also matches before one trailing `\n`, so `value\n` passes and carries the newline into a header, log line, filename, or shell argument | Python: `re.fullmatch()` or `\Z`; PHP: `\z` or the `D` modifier. JavaScript `$` is unaffected unless the `m` flag is set. Grade by sink: a value that never reaches a newline-sensitive sink is not a finding |

## CORS

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true` | Browsers block credentialed response access with a wildcard origin; this combination alone does not establish session theft | Use an explicit origin allowlist for intended credentialed clients; test actual response headers and browser access. A wildcard in *configuration* is not this literal header pair: Starlette/FastAPI `CORSMiddleware(allow_origins=["*"], allow_credentials=True)` and npm `cors({ origin: true, credentials: true })` echo the request's `Origin`, so grade them as the reflecting row below, then check whether session cookies reach cross-site requests (`SameSite=None`) |
| `CORS()` or `CORSMiddleware()` without explicit config | Defaults depend on the package and version; Starlette's CORSMiddleware defaults are restrictive | Inspect the installed middleware and effective configuration before reporting exposure; configure the origins, methods, and headers the application needs |
| Reflecting `Origin` header as `Access-Control-Allow-Origin` | Dynamic CORS that trusts any origin | Validate Origin against allowlist before reflecting |
| `Access-Control-Allow-Methods: *` | All HTTP methods exposed | Whitelist only needed methods |

## Insecure Deserialization / XXE

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `pickle.loads(`, `marshal.loads(`, `yaml.load(` without `Loader=SafeLoader` | Arbitrary object/code execution on untrusted input | `json.loads`, `yaml.safe_load`, or a signed/allowlisted schema |
| `unserialize($` on user input (PHP) | Object injection / POP-chain gadget execution | `json_decode`, or `unserialize($x, ['allowed_classes' => false])` |
| lxml `resolve_entities=True`; PHP `LIBXML_NOENT`/`LIBXML_DTDLOAD`, XMLReader `LIBXML_XINCLUDE`, custom entity loaders; libxmljs `noent: true`; SAX `feature_external_ges=True` | Untrusted XML reaches enabled external-resource loading, allowing file reads or SSRF | Disable external entities/DTDs and XInclude; inspect custom loaders. `LIBXML_NONET` does not block local files. PHP `LIBXML_NO_XXE` requires PHP >=8.4.0 and libxml >=2.13.0 |

## Weak Randomness / TLS Verification

| Search for | Vulnerable pattern | Fix |
|-----------|-------------------|-----|
| `Math.random(`, `random.random(`, `mt_rand(` for tokens/secrets/IDs | Predictable value used as a security control | `crypto.randomBytes`, `secrets.token_urlsafe`, `random_bytes` |
| `verify=False`, `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`; `curl -k`/`--insecure`, `wget --no-check-certificate`, `kubectl --insecure-skip-tls-verify`, `http.sslVerify=false`/`GIT_SSL_NO_VERIFY`, `pip --trusted-host`, `npm config set strict-ssl false` | TLS certificate validation disabled in application, CLI, or CI traffic (MITM) | Remove the bypass; configure the correct CA (`--cacert`, `--certificate-authority`, or the client's trust store) |
| ECB mode, static/reused IV or nonce, home-rolled crypto, MD5/SHA1 for integrity | Deterministic ciphertext, reused nonce, forgeable integrity checks | AES-GCM/ChaCha20-Poly1305 with a fresh nonce, audited libraries, HMAC-SHA256+ |
| `sha256`/`hash_file(`/`hashlib`/signature or HMAC verify on a downloaded, cached, or uploaded artifact (installers, self-updaters, plugin or dependency fetchers) | Integrity check fails open: a missing or malformed digest counts as a pass, a mismatch is only logged or its return value is ignored, a mismatch falls back to a mirror or backend that skips verification, or a cache hit is used without re-verifying | A missing digest is a failure; route every acquisition path, cache reads included, through one verify-then-use helper that refuses the artifact on mismatch. Authenticate the expected digest through trusted provenance, a verified signed manifest, or an authenticated channel; an attacker who can replace both artifact and digest defeats comparison alone. A valid digest proves byte identity only, so archive-extraction checks (File Handling) still apply |

## Version-Gated False Positives

| Pattern | Only a finding when |
|---------|---------------------|
| PHP `assert("...")` string-eval; `preg_replace(...)` with `/e` | PHP < 8.0 (assert removed); PHP < 7.0 (`/e` removed) |
| `yaml.load(..., Loader=FullLoader)` using the historical arbitrary-object construction path | PyYAML < 5.4; verify the actual loader and reachable input. `Loader`, `UnsafeLoader`, and their unsafe C variants still support arbitrary Python construction on later versions; untrusted input reaching those loaders remains reportable. Prefer `safe_load` for untrusted YAML |
| XXE via default entity expansion | Check the parser: lxml `XMLParser` <5.0; `iterparse`/`ETCompatXMLParser` <6.1 ([advisory](https://github.com/lxml/lxml/security/advisories/GHSA-vfmq-68hx-4jfw)); Python SAX <3.7.1. PHP/libxml >=2.9 disables substitution by default, but explicit loading options can restore exposure. `libxml_disable_entity_loader()` is deprecated since PHP 8.0, not inert |
| `jsonwebtoken`/`PyJWT` key-confusion via `kid`/`jku`/`x5u`/`jwk` | `jsonwebtoken` < 9.0.0 (CVE-2022-23540/23539): finding only when all of: `jwt.verify` called with no explicit `algorithms` option and a falsy/empty verification key, or an RSA key accepted for an HS-family algorithm. `PyJWT` < 2.4.0 (CVE-2022-29217): finding only when all of: the app allows both asymmetric and HMAC algorithms and the supplied public key is in a PEM/SSH format the pre-2.4.0 blocklist missed |
| Next.js Server Actions SSRF | Next.js < 14.1.1, CVE-2024-34351: finding only when all of: self-hosted (not Vercel), the `Host` header reaching the app is attacker-controllable, Server Actions are in use, and a Server Action redirects to a relative path |
