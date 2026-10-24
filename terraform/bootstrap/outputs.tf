output "state_bucket_name" {
  description = "The state bucket name; use it in the backend \"s3\" block of the other modules."
  value       = aws_s3_bucket.state.id
}

output "state_bucket_region" {
  description = "The bucket's region; the other modules' backend blocks need it."
  value       = var.aws_region
}
