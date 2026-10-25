variable "aws_region" {
  description = "The single region for the state bucket, server and secrets (aws-setup.md step 2)."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state. The human sets this (bucket names are global)."
  type        = string
}
