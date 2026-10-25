variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  description = "EC2 size. VERIFY: t3.medium holds both Compose projects; t3.small is the fallback."
  type        = string
  default     = "t3.medium"
}

variable "data_volume_gb" {
  description = "Size of the EBS data volume (Postgres per project, on the volume)."
  type        = number
  default     = 30
}

variable "nightly_stop_enabled" {
  description = "On by default. The human switches it off while graders may visit (aws-setup.md step 10)."
  type        = bool
  default     = true
}

variable "nightly_stop_cron" {
  description = "EventBridge Scheduler cron (UTC) for stopping the server each night. VERIFY the expression."
  type        = string
  default     = "cron(0 4 * * ? *)" # 04:00 UTC: after the US evening, before the EU morning (reviewers are in both); turn the stop off while graders may visit
}

variable "secret_names" {
  description = <<-EOT
    Secrets Manager secret names (one JSON secret per environment). NAMES ONLY;
    the human creates the values (aws-setup.md step 8). The instance role is
    granted read on exactly these.
  EOT
  type        = list(string)
  default     = ["vuln-triage/dev", "vuln-triage/prod"]
}

variable "ses_sender_identity_arn" {
  description = <<-EOT
    The verified SES sender identity ARN for task 37 (deferred here). Empty
    disables the SES send permission until the human supplies it.
  EOT
  type        = string
  default     = ""
}
