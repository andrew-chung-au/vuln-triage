# AWS setup for the human

What the human does in AWS and GitHub so the Tier B and C deployment work (B4-B6 and C4 in `_docs/roadmap-tiers-b-c.md`; tasks 17, 18, 21 and 24 in `_docs/tasks.md`) can run. Agents write the CloudFormation templates and the GitHub Actions workflows. The human owns the AWS account, its credentials, money, secrets and DNS. Agents never get AWS credentials (`_docs/architecture.md`, Security boundaries).

Status: guide, 2026-10-22. Written during planning; nothing here has been run. Sources: `_docs/architecture.md` (Deployment, Security boundaries, Open questions 6, 7 and 9, assumptions A26, A36 and A37) and `_docs/roadmap-tiers-b-c.md` (Prerequisites, D1-D3). Where this guide and `architecture.md` differ, `architecture.md` wins and the difference is a defect here. AWS behaviours, prices and console paths are marked `VERIFY:`: check them in the AWS documentation or console when you do the step.

Starting point assumed: you have an AWS account with credits and have hosted apps on EC2 before. Skip any step you have already done, but do the check in each step: older setups often miss one of them (MFA on root, a budget that ignores credits).

## What gets built, and by whom

Five CloudFormation stacks, all in one region, all tagged `project=vuln-triage`:

| Stack | Contents | First deployed by | Updated by |
|---|---|---|---|
| `vt-ci-iam` | GitHub OIDC provider; dev and prod deploy roles | You, once, from the console or your machine | You (changes to IAM are never made by CI) |
| `vt-ecr` | ECR repositories (backend, frontend, responder), keep last 10 images | You, once | You |
| `vt-dev` | One `t3.small` instance running the app in Docker Compose behind a TLS reverse proxy; Postgres on an EBS volume | CI (dev role), on push to `main` | CI |
| `vt-prod` | Same template as `vt-dev`, own parameters and secrets | CI (prod role), manual workflow with your approval | CI, after your approval |
| `vt-observability` | One `t3.medium` instance: Prometheus, Loki, Tempo, Grafana (login required), the responder | CI or you (decided in task 24) | CI or you |

Not used, on purpose (cost): load balancers, NAT gateways, RDS, ECS/EKS, CloudFront. No IAM user or long-lived access key for CI: GitHub Actions assumes the roles through OIDC.

## Checklist

| # | Step | When | Time (rough) |
|---|---|---|---|
| 1 | Account hygiene: root MFA, admin identity, no root keys | Now | 15 min |
| 2 | Pick the region | Now | 5 min |
| 3 | Check the credits | Now | 10 min |
| 4 | Budget and billing alerts that show real spend despite credits | Now, before any stack | 15 min |
| 5 | Decide domain name and TLS (D3, Open question 7) | Before B5 | 30 min + DNS wait |
| 6 | Decide how you reach the instances (SSM or SSH) | Before B5 | 5 min |
| 7 | GitHub: `production` environment and repository variables | Before B4 (environment), after step 8 (variables) | 15 min |
| 8 | Deploy `vt-ci-iam` and `vt-ecr` from the agents' templates | Start of B4, after review | 30 min |
| 9 | Create the secrets | Before B5 (dev), before B6 (prod) | 20 min per environment |
| 10 | Amazon SES sender identity | Before the email path runs in AWS (C1 on dev) | 15 min + DNS wait |
| 11 | Nightly stop and cost-allocation tag | With B5 | 10 min |
| 12 | Teardown after grading | After grading | 30 min |

Steps 1-4 can be done today; none needs any repository code. Steps 5 and 6 are decisions; record them in the issue for task 17.

## 1. Account hygiene

Check, and fix what is missing:
- The root user has MFA, and has no access keys (IAM → Security credentials). Don't use root for anything below except billing settings that need it.
- You sign in day to day as an admin identity with MFA: an IAM Identity Center user (preferred) or an IAM user. VERIFY: Identity Center is free and available in your chosen region.
- If you use the AWS CLI on your machine, it uses that admin identity (for example `aws configure sso`), not root keys.
- Old resources from earlier EC2 projects: list them before starting (EC2 → Instances, Elastic IPs, Volumes, Snapshots; or Resource Explorer, VERIFY). They cost money, and a forgotten Elastic IP or volume is easy to mistake for this project's. This project creates its own VPC resources or uses the default VPC (decided in task 17); it does not reuse old security groups or key pairs.

## 2. Pick the region

One region for every stack, ECR repository, secret and SES identity. Options:
- `ap-southeast-2` (Sydney): lowest latency if you and the reviewers are in Australia.
- `us-east-1` (N. Virginia): usually the lowest prices and the most services; some account-wide settings live there anyway (billing alerts, VERIFY).

Check that SES is available in the region (VERIFY). Record the region as the repository variable `AWS_REGION` (step 7). Recommendation: the region your earlier EC2 apps used, unless prices push you to `us-east-1`.

## 3. Check the credits

Billing and Cost Management → Credits (VERIFY: console path). Note:
- the amount left and the **expiry date**: if it expires before grading, plan the budget as if paying in cash after that date;
- which services the credits cover. Credits often exclude domain registration (Route 53 Domains) and AWS Marketplace (VERIFY on your credit terms). A domain bought through Route 53 may be charged to your card even with credits left.

## 4. Budget and alerts

The architecture asks for a monthly AWS Budgets budget with email alerts at 50 %, 80 % and 100 % (Cost controls). With credits, the default view shows about $0 spend because credits cancel it out, so set the budget to show usage before credits:
1. Billing and Cost Management → Budgets → Create budget → Cost budget, monthly.
2. Amount: your choice (A37). For scale, see "Rough monthly cost" below; a first guess is $40-60 a month for the full stack.
3. In the budget's advanced options, **exclude credits** (and refunds) from the cost, so the alert reflects what the resources really cost (VERIFY: option name, "Credits" under "Charge type" filters).
4. Alerts at 50 %, 80 % and 100 % of actual cost, plus one at 100 % of forecasted cost, sent to your email.

Also worth turning on, free or nearly free (VERIFY): Cost Anomaly Detection with an email subscription, and Free Tier usage alerts if your account is still in the free tier.

## 5. Domain name and TLS (decision D3)

Grafana and the dashboard use session cookies marked `Secure`, so both need HTTPS. The plan has no load balancer or CloudFront, which rules out an AWS Certificate Manager certificate (ACM certificates attach to those, not to a plain EC2 instance; VERIFY). So the certificate comes from Let's Encrypt, obtained by the reverse proxy on each instance.

| Option | What you do | Cost | Notes |
|---|---|---|---|
| A. Domain in Route 53 (recommended if you have none) | Register a cheap domain or point an existing one's name servers to a Route 53 hosted zone | Domain about $10-15/year (often not covered by credits); hosted zone about $0.50/month (VERIFY) | The template can create the DNS records itself, so the instance's address and the name always match |
| B. Domain at another registrar | Add an A record per environment pointing at the instance's Elastic IP | Domain cost only | You update DNS by hand if an Elastic IP changes (it shouldn't; it's kept across stops) |
| C. Subdomain of a domain you already own | As B or A, using `vt-dev.example.com` etc. | None extra | Easiest if you already host apps under a domain |

Names needed: one for dev (for example `dev.<domain>`), one for prod (`app.<domain>`), one for Grafana (`grafana.<domain>`). Each instance gets an Elastic IP so the DNS record stays valid across the nightly stop. Ports 80 and 443 are open to the internet (80 only for the certificate challenge and the redirect to 443).

Proxy choice (Caddy, Traefik or nginx with certbot) is the agents' decision in task 17 and needs your approval as a new image; you only provide the domain.

Without any domain, Let's Encrypt can't issue a normal certificate (VERIFY: short-lived IP-address certificates may now exist), and a self-signed certificate makes reviewers click through a browser warning. Not recommended for graded evidence.

Record in the task 17 issue: the domain, where its DNS is hosted (Route 53 or elsewhere), and the three hostnames.

## 6. How you reach the instances

| Option | What it needs | Recommendation |
|---|---|---|
| AWS Systems Manager Session Manager | The instance role gets the `AmazonSSMManagedInstanceCore` policy; no inbound port; you connect from the console or with the Session Manager plugin for the CLI (VERIFY) | Recommended: no SSH port open, no key pair to lose, sessions logged |
| SSH with a key pair | A key pair in the region; port 22 open to your IP only | Fine if you prefer it; the template takes your IP as a parameter, never `0.0.0.0/0` |

You rarely need either: deploys go through CloudFormation, and logs go to Loki. They are for debugging a failed start.

## 7. GitHub settings

Repository Settings, in `andrew-chung-au/vuln-triage`:
1. **Environments → New environment `production`.** Add yourself as a required reviewer, and restrict deployments to the `main` branch. VERIFY: environment protection rules are available for this repository's plan (they are for public repositories on the free plan, to be confirmed). The prod role's trust policy only accepts tokens from this environment, so no workflow can deploy to prod without your approval.
2. **Secrets and variables → Actions → Variables** (variables, not secrets: none of these is a secret): `AWS_REGION`, and after step 8 `AWS_DEV_ROLE_ARN` and `AWS_PROD_ROLE_ARN` (the role ARNs from the `vt-ci-iam` stack's outputs). Nothing AWS goes in the repository files; the account ID only appears in these variables.
3. **Rulesets:** the `main` ruleset from `_docs/cloud-sessions.md` section 4.2 already refuses direct pushes and needs a pull request. The responder relies on that (it may open pull requests, never push to `main`). No change needed; check it is still Active.

## 8. Bootstrap `vt-ci-iam` and `vt-ecr`

CI can't create the roles it uses to log in, so you deploy these two stacks once by hand. An agent writes both templates in task 17; you deploy them after reviewing the diff.

Before deploying `vt-ci-iam`, check for an existing GitHub OIDC provider: IAM → Identity providers → `token.actions.githubusercontent.com`. An account can have only one provider per URL (VERIFY). If one exists from an earlier project, tell the agent before the template is written, so it reuses the existing provider (a template parameter) instead of failing to create a second one.

Review checklist for `vt-ci-iam` (the template, before you deploy it):
- Trust policy: audience `sts.amazonaws.com`; subject limited to this repository, with `ref:refs/heads/main` for the dev role and `environment:production` for the prod role (VERIFY: the OIDC `sub` claim format). No wildcard over other repositories or pull requests.
- Dev role: push to the three VulnTriage ECR repositories and update `vt-dev` only. Prod role: update `vt-prod` only, with no ECR push. Neither can delete stacks or change IAM.
- Every resource tagged `project=vuln-triage`.

To deploy: CloudFormation → Create stack → Upload the template file from your clean clone (not from an agent's working folder); name it exactly `vt-ci-iam`; tick the IAM capabilities acknowledgement only after the review above. Then `vt-ecr` the same way. Copy the two role ARNs from the `vt-ci-iam` Outputs tab into the GitHub variables (step 7).

## 9. Secrets

The architecture keeps runtime secrets in AWS Secrets Manager, read at container start by the instance role (Security boundaries, secrets table). You create the values; agents only see the secret names, which the template and `.env.example` list. Expected per environment (`dev` and `prod`): database password, Grafana admin password (observability only), SMTP credentials (SES, step 10), LLM API key (Open question 9), the service tokens `N8N_API_TOKEN`, `MCP_API_TOKEN`, `RESPONDER_API_TOKEN`, and the repository read and tracker tokens.

- Generate passwords and tokens with a password manager or `openssl rand -base64 32` on your machine. Never paste a value into an issue, a chat with an agent or a file in the repository.
- Cost: Secrets Manager charges per secret per month (about $0.40, VERIFY). Storing each environment's values as one JSON secret keeps that under $1/month per environment. Whether one JSON secret or one secret per value is the agents' template choice; ask for one per environment if you want the lower cost.
- Alternative: SSM Parameter Store `SecureString` parameters have no per-parameter charge at the standard tier (VERIFY). Using it instead of Secrets Manager is an `architecture.md` change: propose it at task 17 if you prefer it.

Create the dev secrets before the first `vt-dev` deploy (B5), the prod ones before B6.

## 10. Amazon SES (email notifications)

The pilot's channel is email; in AWS it is sent through SES over SMTP (A26).
1. SES → Identities → Create identity: your domain (adds DKIM DNS records; automatic with Route 53) or a single sender address.
2. New accounts start in the SES sandbox: mail only goes to verified addresses (VERIFY). For the pilot and the demo, verify each recipient address (yours and any pilot owners) instead of requesting production access.
3. SMTP credentials: SES → SMTP settings → Create SMTP credentials. Store them in the step 9 secret, not anywhere else.

## 11. Nightly stop and cost tags

- **Nightly stop.** The architecture stops dev and observability instances each night (Cost controls); the schedule itself is in the agents' template (VERIFY: EventBridge Scheduler). You start an instance from the console (EC2 → Instances → Start) before working or demoing. Prod keeps running only while you need it to be reachable for grading.
- **Cost allocation tag.** After the first stack exists, activate the `project` tag in Billing → Cost allocation tags (VERIFY), so Cost Explorer can show this project's spend alone. Tags take about a day to appear.

## Rough monthly cost (if paid without credits)

All figures are on-demand prices in `us-east-1` at the time of writing, as orders of magnitude only (VERIFY in the AWS Pricing Calculator for your region; Sydney is typically 10-25 % higher).

| Item | Count | Approx. per month |
|---|---|---|
| `t3.small` (dev, prod) running 24/7 | 2 | about $15 each |
| `t3.medium` (observability) running 24/7 | 1 | about $30 |
| EBS gp3 root and data volumes, 20-30 GB each | 3 | about $2-3 each |
| Public IPv4 addresses (Elastic IPs; charged whether or not the instance runs) | 3 | about $3.60 each |
| ECR storage (a few GB, lifecycle rule) | — | under $1 |
| Secrets (one JSON secret per environment) | 2-3 | about $0.40 each |
| Route 53 hosted zone (option A) | 1 | about $0.50 |
| Snapshots, data transfer, SES, CloudWatch | — | a few dollars |

Full stack running all the time: roughly $80-90 a month. With the nightly stop of dev and observability (about 12 hours a day) and prod started only near grading: roughly $35-50 a month. The Elastic IPs and volumes are charged even while instances are stopped.

## 12. Teardown

After grading, follow `_docs/architecture.md` Deployment → Teardown, in that order. Then release any Elastic IPs left, delete the budget last, and check Cost Explorer filtered by `project=vuln-triage` a few days later.

## Decisions for the human

Record each answer in the task 17 issue (or the Tier B/C roadmap's D table, for D3) before B4 starts:

| # | Decision | Recommendation |
|---|---|---|
| 1 | Region | The region your earlier EC2 work used, or `ap-southeast-2` if none |
| 2 | Monthly budget amount (A37) | $50 with the 50/80/100 % alerts, credits excluded |
| 3 | Domain and TLS (D3, Open question 7) | An existing domain's subdomains (option C), else a Route 53 domain (option A); Let's Encrypt on the instance |
| 4 | Instance access | Session Manager, no SSH port |
| 5 | Existing GitHub OIDC provider in the account | Tell the agent; reuse it if present |
| 6 | Secrets store | Secrets Manager with one JSON secret per environment, as planned |
| 7 | SES sender | Your domain if you have one in step 5, else one verified address |
