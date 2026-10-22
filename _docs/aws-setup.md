# AWS setup for the human

What the human does in AWS and GitHub so the deployment work (the Deploy phase S3 in `_docs/roadmap.md`; tasks 17, 18, 21 and 22 in `_docs/tasks.md`) can run. Agents write the Terraform files and the GitHub Actions workflows. The human owns the AWS account, its credentials, money, secrets and the first apply. Agents never get AWS credentials (`_docs/architecture.md`, Security boundaries).

Status: guide, current as of 2026-10-22. It describes the design the human chose on 2026-10-22 (Terraform, one server for dev and prod, GHCR, `sslip.io`; decisions H2-H5 in `_docs/roadmap.md`). Written during planning; nothing here has been run. Source: `_docs/architecture.md` (Deployment, Security boundaries, Open questions 6, 7 and 9, assumptions A26, A36 and A37). Where this guide and `architecture.md` differ, `architecture.md` wins and the difference is a defect here. AWS, GHCR, Let's Encrypt and Terraform behaviours, prices and console paths are marked `VERIFY:`: check them in the documentation or console when you do the step.

Starting point assumed: you have an AWS account with credits and have hosted apps on EC2 before. Skip any step you have already done, but do the check in each step: older setups often miss one of them (MFA on root, a budget that ignores credits).

## What gets built, and by whom

Three Terraform modules, all in one region, every resource tagged `project=vuln-triage`. Terraform is the tool; OpenTofu runs the same files. Installing it is a new tool the build task asks you about first.

| Module | Contents | First applied by | Changed by |
|---|---|---|---|
| State bucket | One S3 bucket holding Terraform state (VERIFY: S3-native state locking, so no lock table) | You, once, from your machine | You |
| Deploy role | GitHub OIDC provider (or the account's existing one) and the dev and prod deploy roles | You, once, from your machine | You (changes to IAM are never made by CI) |
| Server | One EC2 instance running the `dev` and `prod` Compose projects behind a TLS reverse proxy, with an Elastic IP, a data volume, snapshots and a nightly stop | You, once, from your machine | You for infrastructure; CI only deploys images onto it |

Images live in GHCR (GitHub's container registry), public, so the server pulls them without a credential (VERIFY). Hostnames come from the server's IP through `sslip.io`, so there is no domain to buy. Dev deploys automatically on a push to `main` when tests pass; production deploys only from a manual workflow you approve. The observability stack, the alert and the responder run in local Compose for submission, not on AWS.

Not used, on purpose (cost): load balancers, NAT gateways, RDS, ECS/EKS, CloudFront, an AWS container registry. No IAM user or long-lived access key for CI: GitHub Actions assumes the roles through OIDC.

What stays human-only: creating and securing the AWS account, the budget alert, creating the secrets, the first `terraform apply`, and teardown. Agents write the files you apply; they never hold AWS credentials, never run `terraform apply` and never see a secret value.

## Checklist

| # | Step | When | Time (rough) |
|---|---|---|---|
| 1 | Account hygiene: root MFA, admin identity, no root keys | Now | 15 min |
| 2 | Pick the region | Now | 5 min |
| 3 | Check the credits | Now | 10 min |
| 4 | Budget and billing alerts that show real spend despite credits | Now, before anything is applied | 15 min |
| 5 | Hostnames and TLS (`sslip.io`, Let's Encrypt) | Before the server is applied | 10 min |
| 6 | Decide how you reach the server (SSM or SSH) | Before the server is applied | 5 min |
| 7 | GitHub: `production` environment, repository variables, public GHCR packages | Before task 21 (environment), after step 8 (variables) | 15 min |
| 8 | Bootstrap: install Terraform, create the state bucket, apply the deploy role and the server | Start of task 17, after review | 45 min |
| 9 | Create the secrets | Before the first dev deploy | 20 min |
| 10 | Email sending route | Before the notification email path runs on AWS | 15 min + wait |
| 11 | Nightly stop and cost-allocation tag | With the server | 10 min |
| 12 | Teardown after grading | After grading | 30 min |

Steps 1-4 can be done today; none needs any repository code. Steps 5 and 6 are decisions; record them in the issue for task 17.

## 1. Account hygiene

Check, and fix what is missing:
- The root user has MFA, and has no access keys (IAM → Security credentials). Don't use root for anything below except billing settings that need it.
- You sign in day to day as an admin identity with MFA: an IAM Identity Center user (preferred) or an IAM user. VERIFY: Identity Center is free and available in your chosen region.
- If you use the AWS CLI on your machine, it uses that admin identity (for example `aws configure sso`), not root keys. Terraform uses the same identity when you run it.
- Old resources from earlier EC2 projects: list them before starting (EC2 → Instances, Elastic IPs, Volumes, Snapshots; or Resource Explorer, VERIFY). They cost money, and a forgotten Elastic IP or volume is easy to mistake for this project's. This project creates its own VPC resources or uses the default VPC (decided in task 17); it does not reuse old security groups or key pairs.

## 2. Pick the region

One region for the state bucket, the server and the secrets. Options:
- `ap-southeast-2` (Sydney): lowest latency if you and the reviewers are in Australia.
- `us-east-1` (N. Virginia): usually the lowest prices and the most services; some account-wide settings live there anyway (billing alerts, VERIFY).

Check that your email route's service is available in the region (step 10, VERIFY). Record the region as the repository variable `AWS_REGION` (step 7). Recommendation: the region your earlier EC2 apps used, unless prices push you to `us-east-1`.

## 3. Check the credits

Billing and Cost Management → Credits (VERIFY: console path). Note:
- the amount left and the **expiry date**: if it expires before grading, plan the budget as if paying in cash after that date;
- which services the credits cover (VERIFY on your credit terms). Nothing in this design buys a domain or uses Marketplace, so those exclusions should not matter.

## 4. Budget and alerts

The architecture asks for a monthly AWS Budgets budget with email alerts at 50 %, 80 % and 100 % (Cost controls). With credits, the default view shows about $0 spend because credits cancel it out, so set the budget to show usage before credits:
1. Billing and Cost Management → Budgets → Create budget → Cost budget, monthly.
2. Amount: your choice (A37). For scale, see "Rough monthly cost" below; a first guess is $30-40 a month.
3. In the budget's advanced options, **exclude credits** (and refunds) from the cost, so the alert reflects what the resources really cost (VERIFY: option name, "Credits" under "Charge type" filters).
4. Alerts at 50 %, 80 % and 100 % of actual cost, plus one at 100 % of forecasted cost, sent to your email.

Also worth turning on, free or nearly free (VERIFY): Cost Anomaly Detection with an email subscription, and Free Tier usage alerts if your account is still in the free tier.

## 5. Hostnames and TLS (`sslip.io`)

Grafana and the dashboard use session cookies marked `Secure`, so both need HTTPS. There is no load balancer or CloudFront, so no AWS Certificate Manager certificate (VERIFY). The certificate comes from Let's Encrypt, obtained by the reverse proxy on the server.

You do not buy or configure a domain. The server has an Elastic IP, and `sslip.io` resolves a hostname containing that IP back to it, for example `dev.203-0-113-10.sslip.io` for dev and `app.203-0-113-10.sslip.io` for prod (VERIFY: the exact `sslip.io` name forms). Ports 80 and 443 are open to the internet (80 only for the certificate challenge and the redirect to 443).

Points to know:
- The Elastic IP must be kept. If it is released, the hostnames change, and every URL in the README with it. It is kept across the nightly stop.
- Let's Encrypt limits how many certificates it issues per name (VERIFY: rate limits). Every sslip.io user shares the `sslip.io` name, so a limit may be hit that you did not cause (VERIFY: whether `sslip.io` is treated as its own registered domain). If issuance fails, the agents' workaround, such as the staging endpoint while testing or `nip.io`, is theirs to propose.
- Proxy choice (Caddy, Traefik or nginx with certbot) is the agents' decision in task 17 and needs your approval as a new image.

Record in the task 17 issue: the two hostnames once the Elastic IP exists.

## 6. How you reach the server

| Option | What it needs | Recommendation |
|---|---|---|
| AWS Systems Manager Session Manager | The instance role gets the `AmazonSSMManagedInstanceCore` policy; no inbound port; you connect from the console or with the Session Manager plugin for the CLI (VERIFY) | Recommended: no SSH port open, no key pair to lose, sessions logged. The deploy workflow may also use SSM Run Command to run the deploy on the server (VERIFY) |
| SSH with a key pair | A key pair in the region; port 22 open to your IP only | Fine if you prefer it; the Terraform variable takes your IP, never `0.0.0.0/0`. Then the deploy mechanism is an architecture change, because CI would need SSH |

You rarely need either for debugging: deploys run from the workflow, and logs are in the local stack's Loki.

## 7. GitHub settings

Repository Settings, in `andrew-chung-au/vuln-triage`:
1. **Environments → New environment `production`.** Add yourself as a required reviewer, and restrict deployments to the `main` branch. VERIFY: environment protection rules are available for this repository's plan (they are for public repositories on the free plan, to be confirmed). The prod role's trust policy only accepts tokens from this environment, so no workflow can deploy to prod without your approval.
2. **Secrets and variables → Actions → Variables** (variables, not secrets: none of these is a secret): `AWS_REGION`, and after step 8 `AWS_DEV_ROLE_ARN` and `AWS_PROD_ROLE_ARN` (the role ARNs from the deploy role module's outputs). Nothing AWS goes in the repository files; the account ID only appears in these variables.
3. **Packages:** after the first image push, set each GHCR package (backend, frontend, responder) to public so the server can pull it without a credential (VERIFY: where the visibility setting lives and that a repository workflow can keep pushing to a package).
4. **Rulesets:** the `main` ruleset from `_docs/cloud-sessions.md` section 4.2 already refuses direct pushes and needs a pull request. The responder relies on that (it may open pull requests, never push to `main`). No change needed; check it is still Active.

## 8. Bootstrap: state bucket, deploy role, server

CI can't create the roles it uses to log in, and Terraform needs somewhere to keep its state, so you do this once by hand, from your machine, as your admin identity. An agent writes the Terraform in task 17; you apply it after reviewing the diff. Nothing in this step gives an agent a credential.

1. Install Terraform on your machine. In the repository, adding it is a tool the build task asks you about. VERIFY: the version the files require.
2. Create the state bucket: apply the bootstrap files with local state, then move the state into the bucket as the agents' README instructs (VERIFY: the exact `init` step).
3. Before applying the deploy role, check for an existing GitHub OIDC provider: IAM → Identity providers → `token.actions.githubusercontent.com`. An account can have only one provider per URL (VERIFY). If one exists from an earlier project, tell the agent before the files are written, so they reuse it (a variable) instead of failing to create a second one.
4. Review the deploy role module before you apply it:
   - Trust policy: audience `sts.amazonaws.com`; subject limited to this repository, with `ref:refs/heads/main` for the dev role and `environment:production` for the prod role (VERIFY: the OIDC `sub` claim format). No wildcard over other repositories or pull requests.
   - Dev role: run the dev deploy on the server only. Prod role: run the production deploy only. Neither can change IAM, Terraform state or the server's configuration.
   - Every resource tagged `project=vuln-triage`.
5. Run `terraform plan`, read it, then `terraform apply` for the deploy role and then the server. Copy the two role ARNs from the outputs into the GitHub variables (step 7), and note the Elastic IP for step 5.

## 9. Secrets

The architecture keeps runtime secrets in AWS Secrets Manager, read at container start by the instance role (Security boundaries, secrets table). You create the values; agents only see the secret names, which the Terraform files and `.env.example` list. Expected per environment (`dev` and `prod`): database password, Grafana admin password (local stack only), SMTP or email-route credentials (step 10), LLM API key (Open question 9), the service tokens `N8N_API_TOKEN`, `MCP_API_TOKEN`, `RESPONDER_API_TOKEN` (those used by showcase components may be left out until built), and the repository read and tracker tokens.

- Generate passwords and tokens with a password manager or `openssl rand -base64 32` on your machine. Never paste a value into an issue, a chat with an agent or a file in the repository.
- Cost: Secrets Manager charges per secret per month (about $0.40, VERIFY). Storing each environment's values as one JSON secret keeps that under $1/month per environment. Ask for one per environment if you want the lower cost.
- Alternative: SSM Parameter Store `SecureString` parameters have no per-parameter charge at the standard tier (VERIFY). Using it instead of Secrets Manager is an `architecture.md` change: propose it at task 17 if you prefer it.

Create the dev secrets before the first dev deploy, the prod ones before the first production deploy.

## 10. Email sending route

For submission the backend sends the top-tier owner notification itself. The route is not yet decided (`_docs/architecture.md`, Routing and notifications, `VERIFY:` with options); the spec says SES (A26). The options:
- Amazon SES over SMTP: SES → Identities → Create identity. `sslip.io` names cannot carry DKIM records you control, so verify a single sender address, not a domain (VERIFY). New accounts start in the SES sandbox: mail only goes to verified addresses (VERIFY), so verify each recipient address you need for the demo. Create SMTP credentials (SES → SMTP settings) and store them in the step 9 secret, nowhere else.
- Amazon SES through the AWS API, using the server's instance role: no SMTP password to store (VERIFY).
- Another SMTP relay: credentials go in the step 9 secret.

Tell the agent which route you choose before the notification email task starts.

## 11. Nightly stop and cost tags

- **Nightly stop.** The server is stopped each night (Cost controls); the schedule itself is in the Terraform (VERIFY: EventBridge Scheduler). You start the server from the console (EC2 → Instances → Start) before working or demoing. Both environments stop together, so keep it running while graders may visit. The Elastic IP is kept, so the hostnames do not change (VERIFY: an Elastic IP stays associated with a stopped instance).
- **Cost allocation tag.** After the first apply, activate the `project` tag in Billing → Cost allocation tags (VERIFY), so Cost Explorer can show this project's spend alone. Tags take about a day to appear.

## Rough monthly cost (if paid without credits)

All figures are on-demand prices in `us-east-1` at the time of writing, as orders of magnitude only (VERIFY in the AWS Pricing Calculator for your region; Sydney is typically 10-25 % higher).

| Item | Count | Approx. per month |
|---|---|---|
| `t3.medium` server running 24/7 (VERIFY: size) | 1 | about $30 |
| EBS gp3 root and data volumes, 20-30 GB | 2 | about $2-3 each |
| Public IPv4 address (Elastic IP; charged whether or not the server runs) | 1 | about $3.60 |
| Secrets (one JSON secret per environment) | 2 | about $0.40 each |
| State bucket, snapshots, data transfer, email, GHCR (public images, VERIFY) | — | a few dollars |

Running all the time: roughly $40 a month. With the nightly stop (about 12 hours a day): roughly $25 a month, because the volumes, snapshots and the Elastic IP are still charged while the server is stopped. After teardown (step 12) the standing cost is about $0: only the state bucket, a few cents, stays until you delete it.

## 12. Teardown

After grading, follow `_docs/architecture.md` Deployment → Teardown, in that order: run `terraform destroy` yourself, delete the snapshots and secrets, delete the budget, and empty and delete the state bucket last. Then release any Elastic IP left, and check Cost Explorer filtered by `project=vuln-triage` a few days later. Teardown is human-only.

## Decisions for the human

Record each answer in the task 17 issue before it starts:

| # | Decision | Recommendation |
|---|---|---|
| 1 | Region | The region your earlier EC2 work used, or `ap-southeast-2` if none |
| 2 | Monthly budget amount (A37) | $40 with the 50/80/100 % alerts, credits excluded |
| 3 | Instance access | Session Manager, no SSH port |
| 4 | Existing GitHub OIDC provider in the account | Tell the agent; reuse it if present |
| 5 | Secrets store | Secrets Manager with one JSON secret per environment, as planned |
| 6 | Email sending route (step 10) | A single verified SES sender address; the route is the open `VERIFY:` in `architecture.md` |
| 7 | Whether to apply Terraform from your machine or a codespace | Your machine, as your admin identity; never CI |
