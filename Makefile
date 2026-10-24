# VulnTriage Makefile. Core targets from _docs/agent-kit/templates/Makefile.mk.
# Project targets (install, test, run) are below.
# Recipe lines must start with a TAB.

help: ## List targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_ -]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: frontend-install backend-install ## Install all dependencies

verify: ## Run the verification gate: make verify [BASE=<commit>]
	@bash _docs/agent-kit/scripts/verify.sh $(BASE)

assert-clean: ## Fail if this folder has uncommitted changes (used after QA)
	@bash _docs/agent-kit/scripts/assert-clean.sh

hooks: ## Install the repo's git hooks (where agents commit; never in a clean clone)
	@bash _docs/agent-kit/scripts/install-hooks.sh

clean-scratch: ## Empty .scratch/ at the end of an issue (refuses while a started process is running)
	@for f in .scratch/*.pid; do if [ -f "$$f" ] && kill -0 "$$(cat "$$f")" 2>/dev/null; then echo "$$f: process $$(cat "$$f") is still running; stop it first"; exit 1; fi; done
	@mkdir -p .scratch && find .scratch -mindepth 1 -delete && echo ".scratch/ is now empty"

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
	@test -e "$(FILE)" || { echo "FILE does not exist: $(FILE)" >&2; exit 1; }
	@test -f "$(FILE)" || { echo "FILE is not a regular file: $(FILE)" >&2; exit 1; }
	@test -s "$(FILE)" || { echo "FILE is empty: $(FILE)" >&2; exit 1; }
	gh api repos/{owner}/{repo}/issues/$(N)/comments -F "body=@$(FILE)"

issue-close: ## Close an issue: make issue-close N=<issue number>
	$(if $(N),,$(error Usage: make issue-close N=<issue number>))
	$(if $(ISSUE_DIGITS_LEFT),$(error N must be an issue number: got '$(N)'))
	gh api -X PATCH repos/{owner}/{repo}/issues/$(N) -f state=closed

.PHONY: issue-dump issue-comment issue-close

tool-versions: ## Print versions of node, npm, uv, python3 and docker (or "<tool>: missing")
	@for t in node npm uv python3 docker; do if command -v "$$t" >/dev/null 2>&1; then printf '%s: ' "$$t"; "$$t" --version; else echo "$$t: missing"; fi; done

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

.PHONY: install test frontend-install backend-install backend-lock frontend-start frontend-stop frontend-build frontend-test backend-test test-unit test-sqlite-integration test-conformance frontend-typecheck frontend-audit dev dev-migrate dev-start dev-stop compose-up compose-down test-integration postgres-integration

test: ## Run all tests (frontend, then backend)
	@$(MAKE) frontend-test
	@$(MAKE) backend-test

frontend-install: ## Install frontend dependencies (npm ci)
	@npm --prefix frontend ci

backend-install: ## Install backend dependencies from backend/uv.lock (uv sync --locked)
	@cd backend && uv sync --locked

backend-lock: ## Update backend/uv.lock after editing backend/pyproject.toml (uv lock)
	@cd backend && uv lock

backend-test: ## Run the backend pytest suite (needs make install first)
	@test -x backend/.venv/bin/pytest || { echo "backend/.venv is missing: run make install first" >&2; exit 1; }
	@backend/.venv/bin/pytest -c backend/pyproject.toml tests

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
