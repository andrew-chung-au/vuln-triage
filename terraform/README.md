# Terraform (task 17 / #141)

The infrastructure for the one-server dev+prod deployment
(`_docs/architecture.md` § Deployment, A36). The agent writes these files; the
**human** installs Terraform, reviews the diff and runs every `terraform apply`
(`_docs/aws-setup.md`). Agents hold no AWS credentials and never apply.

Verify the modules with `_docs/terraform-verify.md` (static checks, the
pre-apply security review, and the per-module and acceptance checks).

## Modules and apply order

Apply once, by hand, in this order (`_docs/aws-setup.md` step 7):

| # | Module | What it creates | State |
|---|---|---|---|
| 1 | `bootstrap/` | the S3 bucket that holds Terraform state (versioned, private, encrypted) | local first, then moved into the bucket |
| 2 | `deploy-roles/` | the GitHub OIDC provider (reused if present) and the `dev`/`prod` deploy roles | the state bucket |
| 3 | `server/` | one EC2 instance, Elastic IP, security group (80/443, SSM, no SSH), instance role, EBS data volume + daily snapshots, the nightly-stop schedule, and a bootstrap that installs Docker + Caddy and the Compose projects | the state bucket |

CI never runs `terraform apply`; it only deploys images onto the server through
the OIDC roles.

## First-time bootstrap (the human)

1. Install Terraform (or OpenTofu) — `VERIFY:` the version the AWS provider needs.
2. `cd terraform/bootstrap` → `terraform init` (local state) → `terraform apply`.
   Then move the state into the new bucket: set the `backend "s3"` block (shown in
   `bootstrap/README-state.md`) and re-run `terraform init` to migrate
   (`VERIFY:` the exact migrate prompt).
3. `cd terraform/deploy-roles` → set `create_oidc_provider` (see below) →
   `terraform init` (S3 backend) → `terraform apply`. Copy the two role ARNs from
   the outputs into the GitHub variables `AWS_DEV_ROLE_ARN` / `AWS_PROD_ROLE_ARN`.
4. `cd terraform/server` → `terraform init` → `terraform apply`. Note the Elastic
   IP from the outputs; record `dev.<eip>.sslip.io` / `app.<eip>.sslip.io` in #141.

Each module takes a `terraform.tfvars` (not committed; copy the
`terraform.tfvars.example`). Every resource is tagged `project=vuln-triage`.

## The `create_oidc_provider` variable

An AWS account may hold only one IAM OIDC provider per URL
(`token.actions.githubusercontent.com`). Before applying `deploy-roles/`, the
human checks IAM → Identity providers:
- none present → set `create_oidc_provider = true` (this module creates it).
- one present → set `create_oidc_provider = false` (this module reuses it by ARN;
  pass `existing_oidc_provider_arn`).

## Defaults (overridable in `terraform.tfvars`)

- `aws_region = "us-east-1"` (decided 2026-10-25: lowest prices; reviewers are in the US and EU)
- `instance_type = "t3.medium"` (`VERIFY:` size; `t3.small` fallback)
- `nightly_stop_enabled = true`
- Reverse proxy: **Caddy** (automatic Let's Encrypt; `server/caddy/Caddyfile`).

All AWS/Terraform/Let's Encrypt behaviours carry `VERIFY:` until checked at apply
time (`_docs/terraform-verify.md` § Notes).
