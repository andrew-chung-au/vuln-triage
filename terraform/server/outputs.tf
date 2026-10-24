output "elastic_ip" {
  description = "The server's public Elastic IP. The sslip.io hostnames embed it."
  value       = aws_eip.server.public_ip
}

output "dev_hostname" {
  description = "The dev dashboard hostname (record in #141)."
  value       = "dev.${replace(aws_eip.server.public_ip, ".", "-")}.sslip.io"
}

output "prod_hostname" {
  description = "The prod dashboard hostname."
  value       = "app.${replace(aws_eip.server.public_ip, ".", "-")}.sslip.io"
}

output "instance_id" {
  description = "The EC2 instance id (for SSM sessions and the deploy workflow)."
  value       = aws_instance.server.id
}
