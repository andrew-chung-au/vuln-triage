# Nightly stop (architecture.md § Cost controls, A37). An EventBridge Scheduler
# rule stops the instance each night; on by default, with an on/off variable the
# human flips off while graders may visit (aws-setup.md step 10). The Elastic IP
# is kept, so the hostnames survive the stop.
# VERIFY: EventBridge Scheduler is the mechanism; the schedule's permission form.

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scheduler_stop" {
  statement {
    effect    = "Allow"
    actions   = ["ec2:StopInstances"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:ResourceTag/project"
      values   = ["vuln-triage"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "vuln-triage-nightly-stop"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler_stop" {
  name   = "stop-instance"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler_stop.json
}

resource "aws_scheduler_schedule" "nightly_stop" {
  count = var.nightly_stop_enabled ? 1 : 0
  name  = "vuln-triage-nightly-stop"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.nightly_stop_cron
  schedule_expression_timezone = "UTC"

  target {
    # The universal EC2 StopInstances target for EventBridge Scheduler.
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ InstanceIds = [aws_instance.server.id] })
  }
}
