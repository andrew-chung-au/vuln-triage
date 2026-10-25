variable "aws_region" {
  type    = string
  default = "ap-southeast-2"
}

variable "github_owner" {
  description = "The GitHub owner of the repository."
  type        = string
  default     = "andrew-chung-au"
}

variable "github_repo" {
  description = "The repository name; the trust policies are scoped to it only."
  type        = string
  default     = "vuln-triage"
}

variable "create_oidc_provider" {
  description = <<-EOT
    Whether to create the GitHub OIDC provider. An account may hold only one
    provider per URL. Set false and pass existing_oidc_provider_arn when the
    account already has one (aws-setup.md step 7.3).
  EOT
  type        = bool
  default     = false
}

variable "existing_oidc_provider_arn" {
  description = "ARN of the account's existing GitHub OIDC provider; used when create_oidc_provider = false."
  type        = string
  default     = ""
}

variable "dev_environment" {
  description = "The GitHub Environment name the dev role's trust policy requires. The deploy-dev job declares it, so its token's sub claim is environment-based, not branch-based; limit that environment's deployment branches to main in GitHub (aws-setup.md step 6.1)."
  type        = string
  default     = "dev"
}

variable "production_environment" {
  description = "The GitHub Environment name the prod role's trust policy requires."
  type        = string
  default     = "production"
}
