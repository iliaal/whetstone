#!/usr/bin/env bash
# skill-patterns.sh — trigger regexes for skill injection (SKILL_PATTERNS).
#
# HAND-MAINTAINED. Generated ONCE from SKILL.md frontmatter (2026-02-22); the
# regexes below have been hand-tuned since — do NOT overwrite this file wholesale.
# scripts/generate-skill-hooks.sh now writes a DRAFT (skill-patterns.draft.sh) for
# NEW skills only; hand-merge new SKILL_PATTERNS entries from that draft into here.
# (--force regenerates in place from raw text and discards tuning — avoid it.)

declare -A SKILL_PATTERNS
declare -A SKILL_TIERS

# SKILL_NEGATIVE — suppression, checked only after SKILL_PATTERNS matches. A skill
# fires when the positive matches AND the negative does not. Optional; almost every
# skill should have no entry.
#
# This exists for ONE shape: a positive alternative that is legitimately
# language-neutral (`segfault`, `\.h\b`, `valgrind`) firing on a prompt that names a
# NEIGHBOURING language. ERE has no lookahead and the hook runs one grep per skill,
# so "X unless Y" is not expressible in the positive pattern.
#
# It is NOT the tool for a positive pattern that is merely too loose. Every misfire
# fixed in this file so far — `AuditControllerTest`, `Avatar.tsx`, `b-UI-lt-in`,
# "PostgreSQL repo", worktree location mentions — was cured by tightening the
# positive (word anchors, bounded gaps, a required intent verb), and each of those
# is a better fix than an exclusion list that has to enumerate the world. Reach for
# a negative only when the excluded thing has an unambiguous name.
declare -A SKILL_NEGATIVE

# --- Tier 1: Methodology (process/approach skills) ---

SKILL_PATTERNS[ia-planning]='plan.*(feature|task|sprint|this|implement|approach|phase|change|refactor|migration)|break.?down.*(feature|task)|implementation.?plan|(create|make|need|start|write|draft|let.?s).*plan|vertical.?slice'
SKILL_TIERS[ia-planning]=1

# Intent-anchored symptoms (2026-07-07 audit-misfire): bare `crash(es)`, unbounded
# `why.*fail`, and `regression.?(test|fix)` fired on security-audit prose ("parser
# crashes"), review rubrics ("why it's wrong (concrete failure)"), and test-coverage
# reviews ("missing regression test") — 35/93 harvested negatives. Fixes: `debug\s`
# (kills `debugging/foo-crash.md` wiki path lists); `why\s+<aux>` question form (rubric
# "why it's/why-real" lacks the aux); crash needs a subject/temporal anchor; regression
# needs a break-symptom not "test/fix". Also replaced PCRE `(?:...)` with plain groups.
SKILL_PATTERNS[ia-debugging]='debug(ging)?\s.{0,30}(error|bug|fail|crash|issue|broken|problem|trace|stack|regression)|fix\s+((the|this)\s+)?bug|why\s+(is|are|was|were|does|did|do|isn.t|doesn.t|won.t|can.t|would|might).{0,30}(fail|crash|broke|error|hang|wrong|null|undefined|throw|freeze|not.?work)|(server|service|app|process|function|test|page|binary|worker|browser|daemon|program|script|query|request|keeps?|still|randomly|intermittent|production|prod|deploy).{0,15}crash(ed|ing|es)?|crash(ed|ing|es).{0,25}(after|when|on.?start|in.?prod|randomly|intermittent|during|deploy|repeatedly|every)|troubleshoot|(analyz|read|paste|inspect|got|this|following).{0,15}stack.?trace|broken.?test|test.{0,10}broken|flaky.?test|regression.{0,15}(bug|broke|broken|fail|introduced|caused)|unexpected.?behav'
SKILL_TIERS[ia-debugging]=1

# Bounded gaps + word anchors (2026-07-07): unbounded `review.*code` / `audit.*code`
# spanned multi-KB prompts and fired on codebases whose domain noun is "audit"
# (AuditControllerTest, audit.enabled) — 16/27 harvested negatives were this misfire.
SKILL_PATTERNS[ia-code-review]='review.{0,60}(\bcode\b|\bprs?\b|\bdiff\b|\bmerge\b)|code.?review|audit(ing)?.{0,20}\b(code|codebase|diff|changes)\b|critiqu'
SKILL_TIERS[ia-code-review]=1

SKILL_PATTERNS[ia-simplifying-code]='simplif\w*\s+(\w+\s+)?code|clean.?up.*code|polish.*code|\brefactor\b|declutter|reduce.?complexity|remove.*(dead.?code|ai.?slop)|improve.?readability'
SKILL_TIERS[ia-simplifying-code]=1

SKILL_PATTERNS[ia-brainstorming]='brainstorm|help.?me.?think|what.?should.?we.?build|explore.{0,40}(approach|idea|option|feature)|compare.{0,30}approach|clarify.{0,30}(requirement|ambigu)|vague.{0,30}(idea|feature|requirement)'
SKILL_TIERS[ia-brainstorming]=1

SKILL_PATTERNS[ia-verification-before-completion]='verif\w*\s.{0,20}(complet|pass|success)|completion.?claim|fresh.?evidence|verify.?before.{0,15}(commit|push|pr|merge|complet)|mark.{0,15}(done|complet)|ready.?to.?merge|claim.{0,30}(fixed|done|complete)'
SKILL_TIERS[ia-verification-before-completion]=1

SKILL_PATTERNS[ia-receiving-code-review]='reviewer.{0,20}(said|suggest|comment|flag|asked)|pr.?comment|mr.?comment|address.{0,30}(review|feedback)|implement.*(suggestion|feedback)|push.?back.*review|respond.*(review|feedback)'
SKILL_TIERS[ia-receiving-code-review]=1

SKILL_PATTERNS[ia-writing-tests]='writ.{0,25}(test|spec)|add.?test|test.?quality|test.?anti.?pattern|mock.*(bad|wrong|instead)|test.?discipline'
SKILL_TIERS[ia-writing-tests]=1


# --- Tier 2: Domain/Language (language/framework-specific) ---

# Bounded gaps + \.php\b (2026-07-07): unbounded `test.*(...).*\.php` spanned
# multi-KB prompts and `\.php` matched inside `.phpt`, injecting into php-src /
# extension C tasks the description explicitly excludes (~10/50 harvested negatives).
SKILL_PATTERNS[ia-php-laravel]='laravel|eloquent|\bblade\b|\bartisan\b|\bphp\b.{0,20}(controller|model|service|middleware|migration|queue|job|route|facade|factory|seeder)|feature.?test.{0,60}\.php\b|unit.?test.{0,60}\.php\b|test.{0,40}(controller|model|service|action|job|command|endpoint).{0,60}\.php\b'
SKILL_TIERS[ia-php-laravel]=2

# React-intent required near .tsx/.jsx (2026-07-07 audit-misfire): bare `\bjsx\b|\btsx\b`
# fired on any .tsx path mention — 53/95 harvested negatives were codesage/MR reviews of
# files like `Avatar.tsx` (paths also contain "components", so a noun anchor doesn't help).
# Replaced with `\b[jt]sx\b` + a runtime SYMPTOM (rendering/broken/error/crash), which path
# noise lacks; bounded the unbounded `react.*test` / `hook.*component` spans.
SKILL_PATTERNS[ia-react-frontend]='react.{0,15}(component|hook|state|context|render|jsx|tsx|router|prop)|next\.?js|react.{0,20}test|\b[jt]sx\b.{0,20}(rendering|re-?render|broken|error|crash|blank|not.?updat|infinite.?loop|undefined)|\bhook[s]?\b.{0,20}component|vitest|component.?test|hook.?test|\brtl\b|testing.?library|snapshot.?test'
SKILL_TIERS[ia-react-frontend]=2

SKILL_PATTERNS[ia-nodejs-backend]='\bexpress\b.*(server|endpoint|route|api)|\bfastify\b|node\.?js.*(backend|server|api)|server.?side.?typescript'
SKILL_TIERS[ia-nodejs-backend]=2

SKILL_PATTERNS[ia-python-services]='\bfastapi\b|python.*(cli|service|backend|api)|async.*python|\bruff\b'
SKILL_TIERS[ia-python-services]=2

SKILL_PATTERNS[ia-rust-systems]='(write|review|refactor|debug|fix|implement|design|structure|optimi[sz]e|port|migrate|test)\b[^.]{0,40}\brust\b|\brust\b.{0,30}(cli|service|binary|workspace|backend|api|server|handler|async|tokio|axum)|async\s+rust|\bcargo\b.{0,20}(build|test|clippy|nextest|workspace|toml|deny)|\bclippy\b|\btokio\b|\baxum\b|\bclap\b.*(derive|parser|subcommand)|\bthiserror\b|\banyhow\b|cargo\.toml|\brustfmt\b|cargo-nextest|rust-toolchain|JoinSet|\bserde\b.*rust|\bcrates?\.io\b|\bcrate\b.{0,25}\bworkspace\b|\bworkspace\b.{0,25}\bcrates?\b'
SKILL_TIERS[ia-rust-systems]=2

# C vs C++ disambiguation has no lookahead available (the hook matches with `grep -qE`
# on a lowercased prompt), and `\bc\b` matches the `c` in `c++` because `+` is a
# non-word char. So every bare-`c` alternative below carries BOTH guards: a leading
# class excluding `-` (kills `objective-c code`) and a required following element that
# `+`/`#` cannot satisfy (kills `c++ code` and `c# code`). Do not simplify either guard
# to a plain `\bc\b` — all three negatives return immediately.
#
# Both patterns must parse under grep -E (the hook) AND Python re (test-triggers).
# POSIX classes like [[:space:]] work only in the former and silently fail the
# Python test. `\s` parses in both but does NOT agree in both: Python's `\s` spans
# newlines while grep is line-oriented, so `c\nfunction` matches in the test and
# not in the hook — the dangerous direction. Separators here are literal spaces.
#
# The leading-class guard only protects the bare-`c` branches. Language-neutral
# alternatives (`\.h\b`, `segfault`, `gdb`, `valgrind`) would still fire on
# `c# segfault` or `MyClass.h in Objective-C`, so SKILL_NEGATIVE below excludes
# those two languages by name. C++ is deliberately absent from that list: a C++
# prompt naming a segfault or a header genuinely wants the C memory rules too, so
# co-firing with ia-cpp-systems is correct.
SKILL_PATTERNS[ia-c-systems]='(^|[^-a-zA-Z0-9_+#])c +(code|function|file|header|module|struct|api|library|extension|program|source|compiler|standard|string|pointer|macro|project|codebase|parser|daemon|driver|allocator|protocol|binary|server|client|buffer|callback|wrapper|routine)\b|(code|written|write|writing|program|library|implement|implemented) +in +c([^+#a-zA-Z0-9_]|$)|\bc(89|99|11|17|23)\b|\.c\b|\.h\b|\bmalloc\b|\bcalloc\b|\brealloc\b|\bmemcpy\b|\bmemmove\b|\bmemset\b|\bstrncpy\b|\bstrlcpy\b|\bsnprintf\b|\bsize_t\b|(u?int(8|16|32|64)_t)|valgrind|address ?sanitizer|\basan\b|\bubsan\b|\bsegfault\b|segmentation fault|\bgdb\b|double ?free|use.?after.?free|dangling pointer|null pointer deref|pointer arithmetic|\-wall\b|\-wextra\b|\-werror\b|\-fsanitize|zend_|\bphpize\b|arginfo|gen_stub|\.phpt\b|config\.m4|php[ _-]?extension'
SKILL_TIERS[ia-c-systems]=2
SKILL_NEGATIVE[ia-c-systems]='\bc#|\bc sharp\b|\bcsharp\b|objective-?c\b|\bdotnet\b|\.cs\b'

SKILL_PATTERNS[ia-cpp-systems]='c\+\+|\bcpp\b|\bcxx\b|\.cpp\b|\.hpp\b|\.cc\b|\.cxx\b|\.hh\b|std::|unique_ptr|shared_ptr|weak_ptr|make_unique|make_shared|\bconstexpr\b|\bnoexcept\b|\bnullptr\b|template *<|\braii\b|move semantics|move constructor|copy constructor|rvalue|rule of (zero|five|three)|virtual (destructor|function)|\bdestructor\b|\bvtable\b|explicit constructor|constructor[^.]{0,25}\bexplicit\b|extern +"?c"? |\bgtest\b|google ?test|\bcatch2\b|clang-tidy|clang-format|\bcmake\b|cmakelists|\bpimpl\b|\bstl\b|string_view|boost::|boost/|\bboost\.(asio|beast|filesystem|program_options|thread|system)\b'
SKILL_TIERS[ia-cpp-systems]=2

# DB-op required near the token (2026-07-07 audit-misfire): bare `postgres`, `jsonb`, and
# `upsert` fired on any prompt naming the stack — 18/44 harvested negatives were Rust
# fix-agent tasks, wiki audits, and reviews mentioning "PostgreSQL repo" as context.
# Each now requires a DB-work word (query/column/migrate/index/...) within a bounded gap.
SKILL_PATTERNS[ia-postgresql]='postgres(ql)?.{0,30}(quer|index|schema|table|column|migrat|partition|tune|optimi|connect|pool|vacuum|explain|perf|slow|lock|tenant|rls|jsonb|constraint|dump|replica)|(quer|schema|migrat|optimi|index|tune|slow|partition|vacuum|explain|connect|pool|deadlock).{0,30}postgres(ql)?|\bpgbouncer\b|jsonb.{0,25}(column|field|index|quer|operator|path|gin|migrat|store|nest|set|->|@>)|row.?level.?security|\brls\b.{0,20}(policy|tenant|postgres|table)|\bcte[s]?\b.{0,30}(query|recurs|select|report)|window.?function|explain.?analyze|partition.{0,40}(range|list|hash|\bby\b)|\bupsert\b.{0,25}(row|record|table|quer|conflict|batch|column|postgres|sql)|tsvector|pg_stat_|pg_class'
SKILL_TIERS[ia-postgresql]=2

SKILL_PATTERNS[ia-terraform]='terraform|opentofu|\biac\b|infrastructure.?as.?code|\bhcl\b|tfvars|tftest'
SKILL_TIERS[ia-terraform]=2

SKILL_PATTERNS[ia-linux-bash-scripting]='bash.?script|shell.?script|linux.?automation|system.?script|cron.?job|deployment.?script'
SKILL_TIERS[ia-linux-bash-scripting]=2

SKILL_PATTERNS[ia-pinescript]='pine.?script|pinescript|tradingview.{0,30}(pine|indicator|strategy|chart|script)|\bindicator\b.{0,20}(pine|trading.?view)|\bstrategy\b.{0,20}(pine|trading.?view)|\.pine\b'
SKILL_TIERS[ia-pinescript]=2

# Word-bounded UI + spaced build verb (2026-07-07 audit-misfire): `ui.*(build|create)`
# matched "b-UI-lt-in", "fast-UU-ID", "b-UI-lder" and any later build/create — 22/36
# harvested negatives were backend code-review prompts (co-injected with php-laravel 21x).
# Fixes: `\bui\b` word-bounds the token; `(design|build)\s` requires a space so CamelCase
# file names like `BuildDashboardProviders.ts` no longer fire; bounded the `frontend.*`
# and `ai.?generated.*` spans.
SKILL_PATTERNS[ia-frontend-design]='frontend.{0,25}(design|redesign|aesthetic|interface|styling)|\bui\b.{0,25}(design|redesign|build|layout|mockup|screen)|(design|redesign|build)\s.{0,20}(web.?component|web.?page|landing.?page|dashboard|hero.?section)|design.{0,20}too.?generic|ai.?generated.{0,20}(design|look|ui)|color.?palette|visual.?identity'
SKILL_TIERS[ia-frontend-design]=2

SKILL_PATTERNS[ia-tailwind-css]='tailwind|@theme.*token|@utility.*css|tailwind.?variant|class.?variance|\bcva\b|\btv\(\b|utility.?class.*css|style.{0,30}utility.?class|dark.?mode.*css'
SKILL_TIERS[ia-tailwind-css]=2

SKILL_PATTERNS[ia-agent-native-architecture]='autonomous.?agent|mcp.?(tool|server)|self.?modif|agent.?(native|loop|hook)|prompt.?native|pretooluse|posttooluse'
SKILL_TIERS[ia-agent-native-architecture]=2

# --- Tier 3: Supporting/Workflow ---

SKILL_PATTERNS[ia-writing]='\brewrite\b|humanize|improve.*text|fix.*(tone|wording)|proofread|remove.*ai.?(language|tell|slop)|ai.?(writing|text).?tell|ai[- ]?tells\b|ai[- ]?slop|ai[- ]?(sounding|written)|(reads?|sounds?).{0,15} (like|as) (an? )?ai\b|\bpr.?description\b|write.*(pull.?request|\bplan\b)'
SKILL_TIERS[ia-writing]=3

# Intent-anchored (2026-07-07): bare `claude\.md` fired on any prompt citing
# CLAUDE.md as reference material (6/6 harvested negatives); unbounded `update.*`
# alternates spanned multi-KB prompts. Verbs required near the doc noun.
SKILL_PATTERNS[ia-md-docs]='update.{0,40}readme|(update|init|create|write|refresh|sync|regenerate|structure).{0,40}agents\.?md|update.{0,40}contributing|update.{0,40}context.?files|(update|create|init|write|refresh|sync|migrate|regenerate|structure).{0,30}claude\.md'
SKILL_TIERS[ia-md-docs]=3

SKILL_PATTERNS[ia-refine-prompt]='refine.{0,15}prompt|improve.{0,15}prompt|promptify|optimize.{0,15}prompt|rewrite.{0,15}prompt|enhance.{0,15}prompt|sharpen.{0,15}instruction|prompt.?engineer|tight.{0,10}system.?prompt|tool.?description|mis-?(pars|interpret|read)'
SKILL_TIERS[ia-refine-prompt]=3

SKILL_PATTERNS[ia-meta-prompting]='/think|/verify|/adversarial|argue.?against|what.?could.?break|deep.?review|meta.?prompt'
SKILL_TIERS[ia-meta-prompting]=3

SKILL_PATTERNS[ia-reflect]='/reflect|session.?review|retrospective|lessons.?learned|what.?went.?wrong'
SKILL_TIERS[ia-reflect]=3

SKILL_PATTERNS[ia-compound-docs]='document.{0,40}(solution|problem|workaround)|capture.{0,40}(knowledge|solved|solution|debug)|compound.{0,30}(doc|knowledge)|post.?mortem'
SKILL_TIERS[ia-compound-docs]=3

SKILL_PATTERNS[ia-document-review]='(refine|polish|review|audit).{0,40}(brainstorm|plan|document|adr|spec)'
SKILL_TIERS[ia-document-review]=3

SKILL_PATTERNS[ia-file-todos]='todo.?directory|manage.?todo|file.?based.?todo'
SKILL_TIERS[ia-file-todos]=3

SKILL_PATTERNS[ia-orchestrating-swarms]='multi.?agent|swarm|parallel.*(agent|task)|divide.?and.?conquer'
SKILL_TIERS[ia-orchestrating-swarms]=3

# Management-intent only (2026-07-07): bare `worktree` matched location mentions
# ("the worktree at /home/ilia/php-src") — 22/22 harvested negatives AND all 44
# "positives" were such mentions. A management verb near the noun is required.
SKILL_PATTERNS[ia-git-worktree]='\b(create|add|new|set.?up|make|remove|clean|prune|switch|list)\b.{0,30}worktrees?|worktrees?.{0,25}(add|create|remove|prune|cleanup|list|switch)\b|parallel.?development'
SKILL_TIERS[ia-git-worktree]=3


# --- Project-type constraints (Tier 2 domain skills only) ---
# Skills listed here are suppressed when the detected project type doesn't match.
# Skills NOT listed pass unconditionally (tier 1 methodology, tier 3 workflow,
# and cross-stack domain skills like postgresql, linux-bash-scripting).
declare -A SKILL_PROJECT_TYPES

SKILL_PROJECT_TYPES[ia-php-laravel]="php"
SKILL_PROJECT_TYPES[ia-react-frontend]="js"
SKILL_PROJECT_TYPES[ia-nodejs-backend]="js"
SKILL_PROJECT_TYPES[ia-python-services]="python"
SKILL_PROJECT_TYPES[ia-terraform]="terraform"
SKILL_PROJECT_TYPES[ia-tailwind-css]="js"
SKILL_PROJECT_TYPES[ia-frontend-design]="js"

# --- Maintenance-context suppression ---
# Skills listed here fire on any prompt mentioning their name (e.g., "the brainstorming
# skill" or "skills/ia-writing-tests/SKILL.md"), which causes high false-positive rates
# during plugin-maintenance tasks (/sync-from-repos, /audit-plugin, distiller runs).
# These skills are suppressed when the prompt is recognized as plugin-maintenance context.
# Evidence: 2026-04-24 audit — brainstorming 85%, writing-tests 100%, planning 100% of
# negative-signal sessions were plugin-maintenance prompts where skill names appeared as
# references rather than user requests.
declare -A SKILL_MAINT_SUPPRESS
SKILL_MAINT_SUPPRESS[ia-brainstorming]=1
SKILL_MAINT_SUPPRESS[ia-writing-tests]=1
SKILL_MAINT_SUPPRESS[ia-planning]=1
# Added 2026-04-27 from analyze-outcomes anomalies (sync run):
# all five fire on plugin-maintenance prompts (audit/sync/release commands name them as references).
SKILL_MAINT_SUPPRESS[ia-verification-before-completion]=1  # 24 sessions, 45.8% neg, +19pp -- "verification" appears in /audit-plugin, /release pre-commit gates
SKILL_MAINT_SUPPRESS[ia-postgresql]=1                       # 10 sessions, 70% neg, +52pp -- "postgresql" mentioned in distiller/audit prompts
SKILL_MAINT_SUPPRESS[ia-react-frontend]=1                   # 6 sessions, 33% neg, +24pp -- skill name still appears in plugin-doc/audit prompts; the `js` project-type guard at line 117 doesn't suppress those references, so MAINT backstops misfires
SKILL_MAINT_SUPPRESS[ia-writing]=1                          # 10 sessions, 20% neg, +12pp -- fires on plugin-doc work
# Added 2026-04-29 from analyze-outcomes anomalies (sync run):
SKILL_MAINT_SUPPRESS[ia-compound-docs]=1                    # 11 sessions, 36.4% neg, +11pp -- "compound" mentioned in /sync-from-repos and /audit-plugin
SKILL_MAINT_SUPPRESS[ia-terraform]=1                        # 7 sessions, 28.6% neg, +10pp -- plugin doesn't use terraform; misfire on audit/sync prompts
SKILL_MAINT_SUPPRESS[ia-python-services]=1                  # 14 sessions, 21.4% neg, +10pp -- fires on distiller.py work in plugin maintenance
# Added 2026-05-02 from diagnose-negatives ia-debugging (post-rename signal verified against pre-rename data):
SKILL_MAINT_SUPPRESS[ia-debugging]=1                        # 4/4 negative cases were plugin-maintenance tasks (auditing, skill restructuring, repo scanning) misfiring as debugging; analyze-outcomes 36% neg on -home-ilia-ai-php

# Total skills: 32
