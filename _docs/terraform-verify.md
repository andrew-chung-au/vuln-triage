# Verifying the Terraform (task 17 / #141)

How to check the `terraform/` modules before and after applying them. The agent
writes the Terraform; **the human runs every `terraform apply`** and performs the
checks in §3-§5 (the agent holds no AWS credentials and never applies —
`_docs/architecture.md` § Security boundaries, `_docs/aws-setup.md`).

This runbook is the single place that says what "the Terraform is verified"
means. It complements, and does not replace:
- `_docs/aws-setup.md` — the ordered human AWS/GitHub runbook (account, region, budget, bootstrap, secrets).
- `_docs/architecture.md` § Deployment — the design the modules implement (modules table, A36, the pipeline, cost controls, teardown).

Modules (see `terraform/README.md` for the layout):

| Module | Path | Applied | State |
|---|---|---|---|
| Bootstrap (state bucket) | `terraform/bootstrap/` | once, by hand | local, then moved into the bucket |
| Deploy roles (OIDC + dev/prod roles) | `terraform/deploy-roles/` | once, by hand | the state bucket |
| Server (EC2, EIP, SG, instance role, schedule) | `terraform/server/` | by hand; CI only deploys images onto it | the state bucket |

## 1. Static checks (no AWS; the agent, CI or the human can run these)

These need only Terraform (or OpenTofu) and no credentials. They catch syntax,
formatting and internal-reference errors. The push-check image already ships
Terraform (`_docs/push-check-image-guide.md`), so these can run there; they do
**not** contact AWS.

Run in each module directory (`terraform/bootstrap`, `terraform/deploy-roles`,
`terraform/server`):

```sh
terraform fmt -check -recursive      # formatting is canonical (fails if not)
terraform init -backend=false        # download providers, no remote state
terraform validate                   # types, references and required args resolve
```

- `terraform fmt -check` must exit 0 (run `terraform fmt -recursive` to fix).
- `terraform validate` must report "Success" in every module.
- `-backend=false` means `init`/`validate` never touch the real state bucket, so
  this is safe to run anywhere, including CI on a pull request.

A green run here proves the files are well-formed and self-consistent. It does
**not** prove the plan is correct against a live account — that is §3.

## 2. Pre-apply review checklist (the human, reading the diff)

Before the first `terraform apply`, read the module and confirm each item. These
are the security-critical properties the design fixes; a miss here is a defect,
not a preference.

Deploy-roles module:
- [ ] OIDC provider: reused when it already exists (the `create_oidc_provider` variable is `false`), created only when absent — one provider per URL per account (`VERIFY:` the account; `_docs/aws-setup.md` step 7.3).
- [ ] Trust policy audience is `sts.amazonaws.com`; subject is limited to **this** repository, `ref:refs/heads/main` for the dev role and `environment:production` for the prod role. No wildcard over other repositories or over pull requests (`VERIFY:` the OIDC `sub` claim format).
- [ ] Dev role can run only the dev deploy on the server; prod role only the production deploy. Neither can change IAM, Terraform state or the server configuration, or read secrets.

Server module:
- [ ] Security group opens **80 and 443 only**; **no SSH (port 22)** and **no key pair**. Access is AWS SSM Session Manager (the instance role has `AmazonSSMManagedInstanceCore`).
- [ ] One Elastic IP, kept across the nightly stop.
- [ ] EBS data volume with daily snapshots.
- [ ] Nightly-stop schedule present, with an on/off variable **on by default**.
- [ ] Instance role SES permission (for task 37) is send-only and scoped to the one verified sender identity; it is not broader. (May be absent until task 37; note which.)

All modules:
- [ ] Every resource is tagged `project=vuln-triage`.
- [ ] No secret value, AWS account id, access key or password appears in any `.tf` file. Secrets are **names only** (Secrets Manager); the account id lives only in the GitHub repository variables (`_docs/aws-setup.md` step 6.2).
- [ ] No resource the plan says is "not used on purpose" (load balancer, NAT gateway, RDS, ECS/EKS, CloudFront, an AWS container registry) is created.

## 3. Apply and per-module verification (the human, with AWS)

Apply in order (`_docs/aws-setup.md` step 7). After each `terraform apply`, run
`terraform plan` again — a clean apply shows **"No changes"** on the second plan
(idempotence). Then the per-module live check:

1. **Bootstrap (state bucket):** `aws s3api get-bucket-versioning` shows versioning enabled; the bucket is private and encrypted (`VERIFY:` the console/CLI path). Then move the state into the bucket as `terraform/README.md` instructs and confirm a later `terraform init` finds it.
2. **Deploy roles:** the two role ARNs appear in `terraform output`. Copy them into the GitHub variables `AWS_DEV_ROLE_ARN` / `AWS_PROD_ROLE_ARN` (`_docs/aws-setup.md` step 6.2). Confirm the trust policy in the console matches §2 (repo, branch/environment conditions).
3. **Server:** `terraform output` names the Elastic IP; the instance is `running`; a Session Manager session connects (no SSH); the `project=vuln-triage` tag is on the instance, volume and EIP. Record the two hostnames `dev.<eip>.sslip.io` and `app.<eip>.sslip.io` in the #141 issue.

## 4. Acceptance for #141 (the dev environment answers)

Task 17's acceptance is end-to-end, so it needs the first deploy (the human runs
it, `_docs/aws-setup.md` steps 6-8). Confirm all of:

- [ ] A push to `main` ran the build-once job: an image tagged `YYYYMMDD-HHMMSS-shortsha` is in GHCR, and the **deploy log names the image digest**.
- [ ] The `dev` Compose project is up on the server behind the reverse proxy.
- [ ] **`https://dev.<elastic-ip>.sslip.io` answers the frontend** (the sign-in page) over HTTPS. If Let's Encrypt refuses the shared `sslip.io` name, the A36 fallback is in effect (staging cert, then `nip.io`); note which was used.
- [ ] `sslip.io` resolves the hostname to the Elastic IP (`VERIFY:` the exact name form).

Record the dev URL, the image tag and its digest in the #141 issue; that is the
evidence the task is done.

## 5. Teardown verification (the human, at end of life)

Follow `_docs/aws-setup.md` step 11 / `_docs/architecture.md` Teardown. After
`terraform destroy` (server, then deploy roles, then empty+delete the state
bucket), confirm **no resource tagged `project=vuln-triage` remains** (Tag Editor
or Resource Groups; `VERIFY:`), the Elastic IP is released, and the next bill
shows no running charges.

## Notes / VERIFY (settled at apply time)

These carry `VERIFY:` in `_docs/architecture.md` / `_docs/aws-setup.md` and are
confirmed against the AWS/Terraform docs when the human applies:

- SSM Run Command (or an equivalent) as the deploy mechanism.
- S3-native state locking (no DynamoDB lock table) in the Terraform version used; if absent, a lock table is added to the bootstrap module.
- `t3.medium` sizing (fallback `t3.small`).
- Let's Encrypt rate limits for the shared `sslip.io` name; the staging-cert / `nip.io` fallback.
- The Terraform version the AWS provider needs, and Terraform's current licence (OpenTofu runs the same files).
