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
data "aws_secretsmanager_secret" "env" {
  for_each = toset(var.secret_names)
  name     = each.value
}

data "aws_iam_policy_document" "secrets_read" {
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [for s in data.aws_secretsmanager_secret.env : s.arn]
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
