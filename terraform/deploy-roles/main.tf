# GitHub OIDC provider and the dev/prod deploy roles (aws-setup.md step 7;
# architecture.md § Security boundaries, the CI-deploy-credentials row).
#
# CI assumes these roles through OIDC with no long-lived AWS key. The trust
# policies are scoped to THIS repository and refuse pull requests and other
# branches. Neither role can change IAM, Terraform state or the server config,
# or read secrets — their IAM policies grant only the deploy action on the
# server (SSM; VERIFY).

# --- OIDC provider: reuse the account's existing one, or create it -----------

# No thumbprint_list: AWS verifies GitHub's OIDC provider against its own library
# of trusted root CAs and no longer uses a pinned thumbprint for it (the argument
# is optional in the AWS provider 5.x; VERIFY at apply time that the plan shows no
# thumbprint error).
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.create_oidc_provider ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

locals {
  oidc_provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_oidc_provider_arn
  repo_sub_prefix   = "repo:${var.github_owner}/${var.github_repo}"
}

# --- Trust policies ----------------------------------------------------------

# Dev role: only tokens from this repo in the `dev` GitHub Environment. The
# deploy-dev job declares `environment: dev`, so GitHub issues its token with an
# environment-based `sub`, not the `ref:` form. The branch limit therefore lives
# in the `dev` environment's deployment-branch setting (main only), not here.
data "aws_iam_policy_document" "dev_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # VERIFY: the OIDC `sub` claim format. No wildcard over other repos or PRs.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["${local.repo_sub_prefix}:environment:${var.dev_environment}"]
    }
  }
}

# Prod role: only tokens from this repo in the `production` GitHub Environment,
# whose deployments the human must approve (aws-setup.md step 6.1).
data "aws_iam_policy_document" "prod_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["${local.repo_sub_prefix}:environment:${var.production_environment}"]
    }
  }
}

# --- Deploy permission -------------------------------------------------------

# The only thing a deploy role may do: run the deploy command on the tagged
# server via SSM (VERIFY: SSM Run Command or an equivalent). It cannot touch
# IAM, S3 state or secrets. Scoped to instances tagged project=vuln-triage.
data "aws_iam_policy_document" "deploy" {
  # SendCommand is authorised against two resources, the target instance and the
  # document. The tag condition only applies to the instance (a document has no
  # project tag), so they are separate statements: one combined statement would
  # fail the condition on the document and deny the call.
  statement {
    sid       = "SendDeployCommandToTaggedInstances"
    effect    = "Allow"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ec2:*:*:instance/*"]
    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/project"
      values   = ["vuln-triage"]
    }
  }
  statement {
    sid       = "UseRunShellScriptDocument"
    effect    = "Allow"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:*::document/AWS-RunShellScript"]
  }
  statement {
    sid       = "ReadCommandResult"
    effect    = "Allow"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }
  # The dev deploy MUST read the instance state before it calls the server, so
  # a deploy to a stopped server (the nightly stop) is skipped and reported and
  # never calls the instance (architecture.md Cost controls (2); task 21/#142).
  # DescribeInstances has no resource-level scoping, so it is read-only on `*`;
  # the role still cannot start, stop or modify the instance.
  statement {
    sid       = "ReadInstanceState"
    effect    = "Allow"
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "dev_deploy" {
  name               = "vuln-triage-dev-deploy"
  assume_role_policy = data.aws_iam_policy_document.dev_trust.json
}

resource "aws_iam_role" "prod_deploy" {
  name               = "vuln-triage-prod-deploy"
  assume_role_policy = data.aws_iam_policy_document.prod_trust.json
}

resource "aws_iam_role_policy" "dev_deploy" {
  name   = "deploy"
  role   = aws_iam_role.dev_deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}

resource "aws_iam_role_policy" "prod_deploy" {
  name   = "deploy"
  role   = aws_iam_role.prod_deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}
