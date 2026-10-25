# Instance role: SSM managed access (Session Manager + Run Command target),
# read on exactly the named secrets, and (when supplied) send-only SES on the
# one verified sender identity (architecture.md § Security boundaries;
# aws-setup.md steps 5, 8, 9).

data "aws_iam_policy_document" "instance_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "vuln-triage-server"
  assume_role_policy = data.aws_iam_policy_document.instance_assume.json
}

# SSM Session Manager and Run Command (the deploy mechanism; VERIFY).
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Read only the named secrets (one JSON secret per environment). The role gets
# no broader Secrets Manager access.
#
# The ARNs are built from the names, not looked up: a data source would fail the
# plan when a secret does not exist yet, and the human adds the prod secret only
# before the first production deploy. Secrets Manager appends a random six-
# character suffix to every secret ARN, so each name is followed by "-??????"
# (the six wildcard characters IAM documents for this).
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "secrets_read" {
  statement {
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      for name in var.secret_names :
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${name}-??????"
    ]
  }
}

resource "aws_iam_role_policy" "secrets_read" {
  name   = "secrets-read"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.secrets_read.json
}

# SES send, only when a verified sender identity is supplied (task 37). Send-only,
# scoped to the one identity, conditioned on the From address.
# VERIFY: ses:SendEmail (and whether SendRawEmail is needed), the resource form,
# and the ses:FromAddress condition key.
data "aws_iam_policy_document" "ses_send" {
  count = var.ses_sender_identity_arn == "" ? 0 : 1
  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = [var.ses_sender_identity_arn]
  }
}

resource "aws_iam_role_policy" "ses_send" {
  count  = var.ses_sender_identity_arn == "" ? 0 : 1
  name   = "ses-send"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.ses_send[0].json
}

resource "aws_iam_instance_profile" "server" {
  name = "vuln-triage-server"
  role = aws_iam_role.instance.name
}
