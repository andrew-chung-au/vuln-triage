# VulnTriage Makefile. Core targets from _docs/agent-kit/templates/Makefile.mk.
# Project targets (install, test, run) are below.
# Recipe lines must start with a TAB.

help: ## List targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_ -]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: frontend-install backend-install responder-install ## Install all dependencies

verify: ## Run the verification gate: make verify [BASE=<commit>]
	@bash _docs/agent-kit/scripts/verify.sh $(BASE)

assert-clean: ## Fail if this folder has uncommitted changes (used after QA)
	@bash _docs/agent-kit/scripts/assert-clean.sh

hooks: ## Install the repo's git hooks (where agents commit; never in a clean clone)
	@bash _docs/agent-kit/scripts/install-hooks.sh

clean-scratch: ## Empty .scratch/ at the end of an issue (refuses while a started process is running)
	@for f in .scratch/*.pid; do if [ -f "$$f" ] && kill -0 "$$(cat "$$f")" 2>/dev/null; then echo "$$f: process $$(cat "$$f") is still running; stop it first"; exit 1; fi; done
	@mkdir -p .scratch && find .scratch -mindepth 1 -delete && echo ".scratch/ is now empty"

check-scripts: ## Syntax-check the kit scripts and the JSON settings (read-only)
	@for f in _docs/agent-kit/scripts/*.sh _docs/agent-kit/claude-code/hooks/cloud_session_start.sh _docs/agent-kit/environments/local-sandbox/pre-push; do bash -n "$$f" || exit 1; done
	@python3 -c 'import ast, sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]' _docs/agent-kit/claude-code/hooks/guard_git.py _docs/agent-kit/claude-code/hooks/verify_on_stop.py _docs/agent-kit/scripts/permission-report.py
	@jq empty opencode.json .claude/settings.json agent-kit/claude-code/settings.json agent-kit/opencode/opencode.json

.PHONY: check-scripts

# --- Project targets (not from the kit) ----------------------------------

# Validates that N is a bare issue number: rejects empty N, and rejects any
# value that still has non-digit characters once the digits are stripped.
ISSUE_DIGITS_LEFT = $(subst 0,,$(subst 1,,$(subst 2,,$(subst 3,,$(subst 4,,$(subst 5,,$(subst 6,,$(subst 7,,$(subst 8,,$(subst 9,,$(N)))))))))))

# issue-comment's FILE must stay under .scratch/ so a typo cannot publish
# another repo file, including .env.
ISSUE_FILE = $(value FILE)
ISSUE_FILE_NOT_SCRATCH = $(if $(filter .scratch/%,$(ISSUE_FILE)),,$(ISSUE_FILE))
ISSUE_FILE_DOTS = $(findstring ..,$(ISSUE_FILE))
ISSUE_FILE_DASH = $(filter -%,$(ISSUE_FILE))

# FILE may use only these characters. This rejects spaces, quotes, '$', ';' and
# newlines before any shell command runs, closing the metacharacter gap in #47.
ISSUE_FILE_CHARS = a b c d e f g h i j k l m n o p q r s t u v w x y z \
	A B C D E F G H I J K L M N O P Q R S T U V W X Y Z \
	0 1 2 3 4 5 6 7 8 9 . _ - /
ISSUE_FILE_CHARS_LEFT = $(call strip_allowed,$(ISSUE_FILE_CHARS),$(value FILE))

# GitHub's comment and body limit is about 65 KB; keep a margin.
MAX_ISSUE_BODY_BYTES = 60000
SCAN_ISSUE_BODY = bash _docs/agent-kit/scripts/scan-issue-body.sh

issue-dump: ## Fetch an issue and its comments as JSON: make issue-dump N=<issue number>
	$(if $(N),,$(error Usage: make issue-dump N=<issue number>))
	$(if $(ISSUE_DIGITS_LEFT),$(error N must be an issue number))
	@mkdir -p .scratch
	gh api repos/{owner}/{repo}/issues/$(N) > .scratch/issue-$(N).json
	@bash -o pipefail -c "gh api --paginate --slurp repos/{owner}/{repo}/issues/$(N)/comments | jq 'add' > .scratch/issue-$(N)-comments.json"
	@echo "Wrote .scratch/issue-$(N).json and .scratch/issue-$(N)-comments.json"

issue-comment: ## Comment on an issue from a file: make issue-comment N=<issue number> FILE=<path under .scratch/>
	$(if $(N),,$(error Usage: make issue-comment N=<issue number> FILE=<path under .scratch/>))
	$(if $(ISSUE_DIGITS_LEFT),$(error N must be an issue number: got '$(N)'))
	$(if $(FILE),,$(error Usage: make issue-comment N=<issue number> FILE=<path under .scratch/>))
	$(if $(filter /%,$(ISSUE_FILE)),$(error FILE must be under .scratch/, not an absolute path: got '$(FILE)'))
	$(if $(ISSUE_FILE_DASH),$(error FILE must not start with '-': got '$(FILE)'))
	$(if $(ISSUE_FILE_DOTS),$(error FILE must not contain '..': got '$(FILE)'))
	$(if $(ISSUE_FILE_NOT_SCRATCH),$(error FILE must be under .scratch/: got '$(FILE)'))
	$(if $(ISSUE_FILE_CHARS_LEFT),$(error FILE may use only letters, digits, '.', '_', '-', '/'; got '$(FILE)'))
	@test ! -L "$(FILE)" || { echo "FILE must not be a symlink: $(FILE)" >&2; exit 1; }
	@test -e "$(FILE)" || { echo "FILE does not exist: $(FILE)" >&2; exit 1; }
	@test -f "$(FILE)" || { echo "FILE is not a regular file: $(FILE)" >&2; exit 1; }
	@test -s "$(FILE)" || { echo "FILE is empty: $(FILE)" >&2; exit 1; }
	@size=$$(wc -c < "$(FILE)"); test "$$size" -le $(MAX_ISSUE_BODY_BYTES) || { echo "FILE is $$size bytes; the limit is $(MAX_ISSUE_BODY_BYTES)" >&2; exit 1; }
	@$(SCAN_ISSUE_BODY) "$(FILE)"
	@if [ "$(DRY_RUN)" = "1" ]; then echo "DRY_RUN: would post $$(wc -c < "$(FILE)") bytes from $(FILE)"; else gh api repos/{owner}/{repo}/issues/$(N)/comments -F "body=@$(FILE)"; fi

issue-close: ## Close an issue: make issue-close N=<issue number>
	$(if $(N),,$(error Usage: make issue-close N=<issue number>))
	$(if $(ISSUE_DIGITS_LEFT),$(error N must be an issue number: got '$(N)'))
	gh api -X PATCH repos/{owner}/{repo}/issues/$(N) -f state=closed

issue-create: ## Create an issue from a file: make issue-create TITLE="..." FILE=<path under .scratch/>
	$(if $(value TITLE),,$(error Usage: make issue-create TITLE="..." FILE=<path under .scratch/>))
	$(if $(filter -%,$(value TITLE)),$(error TITLE must not start with '-': got '$(value TITLE)'))
	$(if $(findstring ',$(value TITLE)),$(error TITLE must not contain a single quote))
	$(if $(FILE),,$(error Usage: make issue-create TITLE="..." FILE=<path under .scratch/>))
	$(if $(filter /%,$(ISSUE_FILE)),$(error FILE must be under .scratch/, not an absolute path: got '$(FILE)'))
	$(if $(ISSUE_FILE_DASH),$(error FILE must not start with '-': got '$(FILE)'))
	$(if $(ISSUE_FILE_DOTS),$(error FILE must not contain '..': got '$(FILE)'))
	$(if $(ISSUE_FILE_NOT_SCRATCH),$(error FILE must be under .scratch/: got '$(FILE)'))
	$(if $(ISSUE_FILE_CHARS_LEFT),$(error FILE may use only letters, digits, '.', '_', '-', '/'; got '$(FILE)'))
	@test ! -L "$(FILE)" || { echo "FILE must not be a symlink: $(FILE)" >&2; exit 1; }
	@test -e "$(FILE)" || { echo "FILE does not exist: $(FILE)" >&2; exit 1; }
	@test -f "$(FILE)" || { echo "FILE is not a regular file: $(FILE)" >&2; exit 1; }
	@test -s "$(FILE)" || { echo "FILE is empty: $(FILE)" >&2; exit 1; }
	@test "$$(printf '%s' '$(value TITLE)' | wc -c)" -le 256 || { echo "TITLE is longer than 256 bytes; shorten it" >&2; exit 1; }
	@size=$$(wc -c < "$(FILE)"); test "$$size" -le $(MAX_ISSUE_BODY_BYTES) || { echo "FILE is $$size bytes; the limit is $(MAX_ISSUE_BODY_BYTES)" >&2; exit 1; }
	@$(SCAN_ISSUE_BODY) "$(FILE)"
	@if [ "$(DRY_RUN)" = "1" ]; then echo "DRY_RUN: would create an issue from $(FILE)"; else gh issue create --title '$(value TITLE)' --body-file "$(FILE)"; fi

.PHONY: issue-dump issue-comment issue-close issue-create

tool-versions: ## Print versions of node, npm, uv, python3 and docker (or "<tool>: missing")
	@for t in node npm uv python3 docker; do if command -v "$$t" >/dev/null 2>&1; then printf '%s: ' "$$t"; "$$t" --version; else echo "$$t: missing"; fi; done

# --- Read-only git and GitHub helpers (permission sweep) -----------------

# CONTAINS and REF must be hex; the check runs before any shell command, so a
# space, '$', quote or other character is refused. CI_LIMIT and CI_RUN are
# digits only, for the same reason.
DIGITS = 0 1 2 3 4 5 6 7 8 9

BRANCH_CONTAINS = $(value CONTAINS)
BRANCH_CONTAINS_HEX_LEFT = $(call strip_allowed,$(SINCE_HEX_DIGITS),x$(BRANCH_CONTAINS)x)

CI_WORKFLOW = $(value WORKFLOW)
CI_WORKFLOW_CHARS = a b c d e f g h i j k l m n o p q r s t u v w x y z \
	A B C D E F G H I J K L M N O P Q R S T U V W X Y Z \
	0 1 2 3 4 5 6 7 8 9 . _ -
CI_WORKFLOW_CHARS_LEFT = $(call strip_allowed,$(CI_WORKFLOW_CHARS),$(value WORKFLOW))
CI_LIMIT = $(value LIMIT)
CI_LIMIT_CHARS_LEFT = $(call strip_allowed,$(DIGITS),$(value LIMIT))

CI_RUN = $(value RUN)
CI_RUN_DIGITS_LEFT = $(subst 0,,$(subst 1,,$(subst 2,,$(subst 3,,$(subst 4,,$(subst 5,,$(subst 6,,$(subst 7,,$(subst 8,,$(subst 9,,$(CI_RUN)))))))))))

REF = $(value REF)
REF_HEX_LEFT = $(call strip_allowed,$(SINCE_HEX_DIGITS),x$(REF)x)
FILE_AT = $(value FILE)
FILE_AT_CHARS_LEFT = $(call strip_allowed,$(ISSUE_FILE_CHARS),$(value FILE))
FILE_AT_DOTS = $(findstring ..,$(FILE_AT))
FILE_AT_DASH = $(filter -%,$(FILE_AT))
FILE_AT_SECRET = $(filter-out %.env.example,$(filter .env %.env %.env.% %.pem %.key %id_rsa% %id_ed25519% id_rsa id_ed25519 %/id_rsa %/id_ed25519,$(FILE_AT)))

.PHONY: branches ci ci-run file-at

branches: ## List branches (read-only): make branches [CONTAINS=<commit>]
	$(if $(filter xx,$(BRANCH_CONTAINS_HEX_LEFT)),,$(error CONTAINS must be 7 to 40 lowercase hex characters, a commit; got '$(value CONTAINS)'))
	@test -z "$(BRANCH_CONTAINS)" || { n=$$(printf '%s' "$(BRANCH_CONTAINS)" | wc -c); test "$$n" -ge 7 && test "$$n" -le 40 || { echo "CONTAINS must be 7 to 40 hex characters; got '$(BRANCH_CONTAINS)'" >&2; exit 1; }; }
	@git branch -a --no-color $(if $(BRANCH_CONTAINS),--contains $(BRANCH_CONTAINS),)

ci: ## List CI runs (read-only): make ci [WORKFLOW=<name>] [LIMIT=<1-100>]
	$(if $(CI_WORKFLOW_CHARS_LEFT),$(error WORKFLOW may use only letters, digits, '.', '_' and '-'; got '$(value WORKFLOW)'))
	$(if $(CI_LIMIT_CHARS_LEFT),$(error LIMIT must be a number 1-100; got '$(value LIMIT)'))
	@if [ -n "$(CI_LIMIT)" ]; then test "$(CI_LIMIT)" -ge 1 && test "$(CI_LIMIT)" -le 100 || { echo "LIMIT must be 1-100; got '$(CI_LIMIT)'" >&2; exit 1; }; fi
	@gh run list $(if $(CI_WORKFLOW),--workflow "$(CI_WORKFLOW)",) $(if $(CI_LIMIT),--limit "$(CI_LIMIT)",)

ci-run: ## Show one CI run (read-only): make ci-run RUN=<run id>
	$(if $(CI_RUN),,$(error Usage: make ci-run RUN=<run id>))
	$(if $(CI_RUN_DIGITS_LEFT),$(error RUN must be a numeric run id: got '$(value RUN)'))
	@gh run view "$(CI_RUN)"

file-at: ## Show a file at a commit (read-only): make file-at REF=<commit> FILE=<path>
	$(if $(REF),,$(error Usage: make file-at REF=<commit> FILE=<path>))
	$(if $(filter xx,$(REF_HEX_LEFT)),,$(error REF must be 7 to 40 lowercase hex characters, a commit; got '$(value REF)'))
	$(if $(FILE_AT),,$(error Usage: make file-at REF=<commit> FILE=<path>))
	$(if $(filter /%,$(FILE_AT)),$(error FILE must be relative: got '$(FILE)'))
	$(if $(FILE_AT_DASH),$(error FILE must not start with '-': got '$(FILE)'))
	$(if $(FILE_AT_DOTS),$(error FILE must not contain '..': got '$(FILE)'))
	$(if $(FILE_AT_CHARS_LEFT),$(error FILE may use only letters, digits, '.', '_', '-', '/'; got '$(FILE)'))
	$(if $(FILE_AT_SECRET),$(error FILE must not name a secret file: got '$(FILE)'))
	@test "$$(printf '%s' "$(REF)" | wc -c)" -ge 7 && test "$$(printf '%s' "$(REF)" | wc -c)" -le 40 || { echo "REF must be 7 to 40 hex characters; got '$(REF)'" >&2; exit 1; }
	@git show "$(REF):$(FILE_AT)"

# --- Permission report (issue #61) ---------------------------------------

# SINCE must be 7 to 40 lowercase hex characters naming a commit. Make checks
# the characters here, before any shell command runs: after every hex digit is
# removed, "x<SINCE>x" must be exactly "xx", so a space, a newline, '$', a
# quote, '-' or any other character is refused. $(value SINCE) keeps a typed
# '$(...)' from being expanded. The script then checks the length and that
# SINCE is a commit, again before running anything else.
SINCE_HEX_DIGITS = 0 1 2 3 4 5 6 7 8 9 a b c d e f
SINCE_CHARS_LEFT = $(call strip_allowed,$(SINCE_HEX_DIGITS),x$(value SINCE)x)

.PHONY: permission-report

permission-report: ## Count approvals recorded in session summaries (read-only): make permission-report SINCE=<commit>
	$(if $(value SINCE),,$(error Usage: make permission-report SINCE=<commit>  (7 to 40 lowercase hex characters, a commit)))
	$(if $(filter xx,$(SINCE_CHARS_LEFT)),,$(error SINCE must be 7 to 40 lowercase hex characters, a commit; got '$(value SINCE)'. Usage: make permission-report SINCE=<commit>))
	@python3 _docs/agent-kit/scripts/permission-report.py "$(value SINCE)"

# --- API contract (issue #23) --------------------------------------------

# OPENAPI must stay a relative path under _docs/ or .scratch/ with only
# letters, digits, '.', '_', '-', '/', and no '..'. These are pure make
# functions, so a bad value stops make before any shell command runs.
OPENAPI ?= _docs/openapi.yaml
OPENAPI_ALLOWED_CHARS = a b c d e f g h i j k l m n o p q r s t u v w x y z \
	A B C D E F G H I J K L M N O P Q R S T U V W X Y Z \
	0 1 2 3 4 5 6 7 8 9 . _ - /

strip_allowed = $(if $(1),$(call strip_allowed,$(wordlist 2,$(words $(1)),$(1)),$(subst $(firstword $(1)),,$(2))),$(2))

OPENAPI_CHARS_LEFT = $(call strip_allowed,$(OPENAPI_ALLOWED_CHARS),$(value OPENAPI))
OPENAPI_BAD_PREFIX = $(if $(filter _docs/% .scratch/%,$(value OPENAPI)),,$(value OPENAPI))
OPENAPI_BAD_DOTS = $(findstring ..,$(value OPENAPI))
OPENAPI_INVALID = $(strip $(OPENAPI_CHARS_LEFT)$(OPENAPI_BAD_PREFIX)$(OPENAPI_BAD_DOTS))

.PHONY: openapi-validate

openapi-validate: ## Validate an OpenAPI contract: make openapi-validate [OPENAPI=<path>]
	$(if $(OPENAPI_INVALID),$(error OPENAPI must stay under _docs/ or .scratch/, use only letters, digits, '.', '_', '-', '/', and contain no '..'; got '$(value OPENAPI)'))
	@uvx openapi-spec-validator==0.9.0 "$(OPENAPI)"

# --- Frontend (issue #15 E2) ---------------------------------------------

.PHONY: install test frontend-install backend-install responder-install backend-lock responder-lock frontend-start frontend-stop frontend-build frontend-test backend-test responder-test test-unit test-sqlite-integration test-conformance frontend-typecheck frontend-audit dev dev-migrate dev-start dev-stop compose-up compose-down test-integration postgres-integration

test: ## Run all tests (frontend, then backend, then responder)
	@$(MAKE) frontend-test
	@$(MAKE) backend-test
	@$(MAKE) responder-test

frontend-install: ## Install frontend dependencies (npm ci)
	@npm --prefix frontend ci

backend-install: ## Install backend dependencies from backend/uv.lock (uv sync --locked)
	@cd backend && uv sync --locked

responder-install: ## Install responder dependencies from responder/uv.lock (uv sync --locked)
	@cd responder && uv sync --locked

backend-lock: ## Update backend/uv.lock after editing backend/pyproject.toml (uv lock)
	@cd backend && uv lock

responder-lock: ## Update responder/uv.lock after editing responder/pyproject.toml (uv lock)
	@cd responder && uv lock

backend-test: ## Run the backend pytest suite (needs make install first)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/pytest -c backend/pyproject.toml -m "not compose" tests

responder-test: ## Run the responder pytest suite (needs make install first)
	@test -x responder/.venv/bin/pytest || { echo "responder/.venv is missing: run make install first" >&2; exit 1; }
	@responder/.venv/bin/pytest -c responder/pyproject.toml responder/tests

# Marker-scoped backend subsets for the CI jobs (issue #139, task 19). Each is a
# slice of backend-test; `make test` still runs them all for the local gate.
test-unit: ## Run the backend unit-marked cases only (CI `unit` job)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/pytest -c backend/pyproject.toml -m unit tests

test-sqlite-integration: ## Run the backend SQLite integration-marked cases only (CI `sqlite-integration` job)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/pytest -c backend/pyproject.toml -m sqlite_integration tests

test-conformance: ## Run the OpenAPI conformance test only (CI `openapi-validation` job)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/pytest -c backend/pyproject.toml tests/test_openapi_conformance.py

frontend-test: ## Run the frontend unit tests (vitest run)
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@npm --prefix frontend test

frontend-typecheck: ## Type-check the frontend (tsc --noEmit; vite build does not run tsc)
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@cd frontend && ./node_modules/.bin/tsc --noEmit

frontend-audit: ## Audit frontend dependencies (npm audit)
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@cd frontend && npm audit

frontend-build: ## Build the frontend production output (vite build)
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@npm --prefix frontend run build

frontend-start: ## Start the frontend Vite dev server in the background (log: .scratch/frontend.log)
	@mkdir -p .scratch
	@if [ -f .scratch/frontend.pid ] && kill -0 "$$(cat .scratch/frontend.pid)" 2>/dev/null; then echo "frontend is already running (pid $$(cat .scratch/frontend.pid))"; exit 1; fi
	@cd frontend && nohup ./node_modules/.bin/vite dev --host 127.0.0.1 --port 5173 > ../.scratch/frontend.log 2>&1 & echo $$! > .scratch/frontend.pid
	@echo "frontend started (pid $$(cat .scratch/frontend.pid)); log: .scratch/frontend.log"

frontend-stop: ## Stop the frontend started by frontend-start
	@if [ ! -f .scratch/frontend.pid ]; then echo "frontend is not running"; exit 0; fi; \
	pid=$$(cat .scratch/frontend.pid); kill "$$pid" 2>/dev/null; \
	for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$$pid" 2>/dev/null || break; sleep 1; done; \
	if kill -0 "$$pid" 2>/dev/null; then echo "frontend (pid $$pid) did not stop within 10 s"; exit 1; fi; \
	rm -f .scratch/frontend.pid; echo "frontend stopped"

# --- Fixture recorder (issue #76) ----------------------------------------

# SOURCE must be exactly one of these words; make checks it before any shell command runs.
RECORD_SOURCES = github osv kev epss all

.PHONY: record-fixtures

record-fixtures: ## Record live fixtures (run by the human; public APIs, no token): make record-fixtures SOURCE=<github|osv|kev|epss|all>
	$(if $(value SOURCE),,$(error Usage: make record-fixtures SOURCE=<github|osv|kev|epss|all>))
	$(if $(or $(filter-out $(RECORD_SOURCES),$(value SOURCE)),$(word 2,$(value SOURCE))),$(error SOURCE must be exactly one of: $(RECORD_SOURCES); got '$(value SOURCE)'))
	@test -x backend/.venv/bin/python || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/python tests/record_fixtures.py "$(value SOURCE)"

# --- Dev run (issue #133): backend on SQLite + frontend together ---------

dev-migrate: ## Create or upgrade the dev SQLite schema (alembic upgrade head)
	@test -x backend/.venv/bin/python || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@cd backend && uv run alembic upgrade head

dev: dev-migrate ## Run backend (SQLite) and frontend dev server together; Ctrl-C stops both (no Docker)
	@echo "Starting backend on 127.0.0.1:8000 and frontend on 127.0.0.1:5173 (Ctrl-C to stop)"
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@mkdir -p .scratch
	@( cd backend && exec uv run uvicorn vulntriage.main:app --host 127.0.0.1 --port 8000 ) & \
	backend_pid=$$!; \
	trap 'kill "$$backend_pid" 2>/dev/null' INT TERM EXIT; \
	cd frontend && ./node_modules/.bin/vite dev --host 127.0.0.1 --port 5173

dev-start: dev-migrate ## Start backend and frontend in the background (logs in .scratch/; stop with make dev-stop)
	@test -d frontend/node_modules || { echo "frontend/node_modules is missing: run make install first" >&2; exit 1; }
	@mkdir -p .scratch
	@if [ -f .scratch/dev-backend.pid ] && kill -0 "$$(cat .scratch/dev-backend.pid)" 2>/dev/null; then echo "dev backend already running (pid $$(cat .scratch/dev-backend.pid))"; exit 1; fi
	@if [ -f .scratch/dev-frontend.pid ] && kill -0 "$$(cat .scratch/dev-frontend.pid)" 2>/dev/null; then echo "dev frontend already running (pid $$(cat .scratch/dev-frontend.pid))"; exit 1; fi
	@cd backend && nohup uv run uvicorn vulntriage.main:app --host 127.0.0.1 --port 8000 > ../.scratch/dev-backend.log 2>&1 & echo $$! > .scratch/dev-backend.pid
	@cd frontend && nohup ./node_modules/.bin/vite dev --host 127.0.0.1 --port 5173 > ../.scratch/dev-frontend.log 2>&1 & echo $$! > .scratch/dev-frontend.pid
	@echo "dev backend (pid $$(cat .scratch/dev-backend.pid)) and frontend (pid $$(cat .scratch/dev-frontend.pid)) started; logs: .scratch/dev-backend.log, .scratch/dev-frontend.log"

dev-stop: ## Stop the processes started by dev-start
	@for name in dev-backend dev-frontend; do \
	  if [ -f .scratch/$$name.pid ]; then pid=$$(cat .scratch/$$name.pid); kill "$$pid" 2>/dev/null; \
	    for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$$pid" 2>/dev/null || break; sleep 1; done; \
	    if kill -0 "$$pid" 2>/dev/null; then echo "$$name (pid $$pid) did not stop within 10 s"; exit 1; fi; \
	    rm -f .scratch/$$name.pid; echo "$$name stopped"; \
	  else echo "$$name is not running"; fi; \
	done

# --- Local reviewer demo ----------------------------------------------------
# One command: migrate, create a demo security lead, start the app on the
# recorded fixtures (no Docker, no network) and register four demo repositories
# through the API. The demo password is public by design and works only on this
# local database. VT_FEEDS=fixtures is refused unless DEPLOYMENT_ENVIRONMENT is
# dev or test, so it cannot run in production.
DEMO_USER = lead
DEMO_PASSWORD = demo-password-local

demo: dev-migrate ## Start the app on recorded fixtures with a demo login and four demo repositories (local, no Docker, no network)
	@printf '%s\n' '$(DEMO_PASSWORD)' | uv run --directory backend python -m vulntriage.manage create-user --username $(DEMO_USER) --display-name "Security Lead" --email lead@example.com --role "security lead" || echo "note: the demo user was not created (it may already exist)"
	@$(MAKE) dev-start VT_FEEDS=fixtures DEPLOYMENT_ENVIRONMENT=dev
	@VT_SEED_PASSWORD='$(DEMO_PASSWORD)' python3 deploy/seed-pilot.py --base-url http://127.0.0.1:8000 --username $(DEMO_USER) --seed-file deploy/demo-seed.json --wait 60
	@echo "Open http://127.0.0.1:5173 and sign in as $(DEMO_USER) / $(DEMO_PASSWORD). Stop with: make dev-stop"

demo-reset: ## Stop the app and delete the local dev database, so make demo starts clean
	@$(MAKE) dev-stop
	@rm -f backend/.scratch/vulntriage.db
	@echo "dev database removed"

.PHONY: demo demo-reset

# --- Compose stack (issue #137, task 15) ---------------------------------
# The full application stack (frontend, backend, Postgres) on one origin.
# Needs Docker and a .env (copy .env.example). Runs on the human's host or in
# CI, not in the agent sandbox.

compose-up: ## Build and start the full app stack (frontend, backend, Postgres); needs a .env
	@test -f .env || { echo ".env is missing: copy .env.example to .env and fill it in" >&2; exit 1; }
	@docker compose up --build -d --wait

compose-down: ## Stop the app stack (add CLEAN=1 to also remove the Postgres volume)
	@docker compose down $(if $(CLEAN),--volumes,)

# --- Real-Postgres integration tests (issue #138, task 16) ---------------
# Run the integration cases against Postgres in the vt-test Compose project.
# Needs Docker; runs in CI or on the human's host, not the agent sandbox.

test-integration: ## Run the integration cases against Postgres (vt-test Compose project)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@bash ci/test-integration.sh

postgres-integration: test-integration ## CI alias for the postgres-integration job (task 19 wires it in)

# --- Compose telemetry/alert/responder tests (issue #157, task 25) -------
# Run the selected JOB's cases against the observability stack in Compose.
# Needs Docker; runs in CI (the telemetry/alert/responder jobs) or on the
# human's host, not the agent sandbox. JOB must be one of telemetry, alert,
# responder (or empty: run all three, for the human's host). The cases are
# `compose`-marked and deselected by `make test`/`make verify`.
#
# #157 implements the `telemetry` job (and this selector); `alert` and
# `responder` are tasks 27 (#159) and 28 (#160, #220). `T-JOURNEY-BE` (the full
# scan journey) needs the backend feed-fixture wiring of prerequisite #172.

# JOB, when set, must be exactly one of these words; make checks it before any
# shell command runs, mirroring the SOURCE/OPENAPI validation idiom above.
COMPOSE_JOBS = telemetry alert responder

.PHONY: test-compose

test-compose: ## Run a Compose telemetry/alert/responder job: make test-compose [JOB=<telemetry|alert|responder>]
	$(if $(value JOB),$(if $(or $(filter-out $(COMPOSE_JOBS),$(value JOB)),$(word 2,$(value JOB))),$(error JOB must be exactly one of: $(COMPOSE_JOBS); got '$(value JOB)')),)
	@JOB="$(value JOB)" bash ci/test-compose.sh
