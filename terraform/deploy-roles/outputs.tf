output "dev_role_arn" {
  description = "Set as the GitHub repository variable AWS_DEV_ROLE_ARN (aws-setup.md step 6.2)."
  value       = aws_iam_role.dev_deploy.arn
}

output "prod_role_arn" {
  description = "Set as the GitHub repository variable AWS_PROD_ROLE_ARN (aws-setup.md step 6.2)."
  value       = aws_iam_role.prod_deploy.arn
}
