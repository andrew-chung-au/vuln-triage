# VulnTriage Makefile. Core targets from _docs/agent-kit/templates/Makefile.mk.
# install/test/run targets will be added when the project is scaffolded.
# Recipe lines must start with a TAB.

help: ## List targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_ -]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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

issue-dump: ## Fetch an issue as JSON: make issue-dump N=<issue number>
	$(if $(N),,$(error Usage: make issue-dump N=<issue number>))
	$(if $(ISSUE_DIGITS_LEFT),$(error N must be an issue number))
	@mkdir -p .scratch
	gh issue view $(N) --json number,title,body,state,labels,comments > .scratch/issue-$(N).json
	@echo "Wrote .scratch/issue-$(N).json"

tool-versions: ## Print versions of node, npm, uv, python3 and docker (or "<tool>: missing")
	@for t in node npm uv python3 docker; do if command -v "$$t" >/dev/null 2>&1; then printf '%s: ' "$$t"; "$$t" --version; else echo "$$t: missing"; fi; done

# --- Frontend (issue #15 E2) ---------------------------------------------

.PHONY: test frontend-install frontend-start frontend-stop frontend-test

test: ## Run all tests (currently the frontend's)
	@$(MAKE) frontend-test

frontend-install: ## Install frontend dependencies (npm ci)
	@npm --prefix frontend ci

frontend-test: ## Run the frontend unit tests (vitest run)
	@npm --prefix frontend test

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
