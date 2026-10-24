# GitHub OIDC provider and the dev/prod deploy roles (aws-setup.md step 7;
# architecture.md § Security boundaries, the CI-deploy-credentials row).
#
# CI assumes these roles through OIDC with no long-lived AWS key. The trust
# policies are scoped to THIS repository and refuse pull requests and other
# branches. Neither role can change IAM, Terraform state or the server config,
# or read secrets — their IAM policies grant only the deploy action on the
# server (SSM; VERIFY).

# --- OIDC provider: reuse the account's existing one, or create it -----------

# GitHub's current OIDC thumbprint list is maintained by AWS for this well-known
# provider; VERIFY the thumbprint requirement for your provider/region (recent
# AWS no longer pins a thumbprint for IAM OIDC with GitHub).
resource "aws_iam_openid_connect_provider" "github" {
  count           = var.create_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"] # VERIFY: current thumbprint, or omit per AWS guidance
}

locals {
  oidc_provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_oidc_provider_arn
  repo_sub_prefix   = "repo:${var.github_owner}/${var.github_repo}"
}

# --- Trust policies ----------------------------------------------------------

# Dev role: only tokens from this repo on the main branch.
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
      values   = ["${local.repo_sub_prefix}:ref:refs/heads/main"]
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
  statement {
    sid     = "SendDeployCommand"
    effect  = "Allow"
    actions = ["ssm:SendCommand"]
    # The document that runs the deploy, plus instances carrying the project tag.
    resources = [
      "arn:aws:ssm:*::document/AWS-RunShellScript",
      "arn:aws:ec2:*:*:instance/*",
    ]
    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/project"
      values   = ["vuln-triage"]
    }
  }
  statement {
    sid       = "ReadCommandResult"
    effect    = "Allow"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
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
