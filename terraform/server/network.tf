# Network: default VPC, a security group opening only 80 and 443, and an
# Elastic IP kept across the nightly stop (architecture.md § Deployment, A36).
# No SSH (port 22) and no key pair — access is AWS SSM Session Manager
# (aws-setup.md step 5).

data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "server" {
  name        = "web-http-https"
  description = "Public web server: HTTP and HTTPS in, all out. No SSH (SSM only)."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP (ACME challenge and redirect to 443)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS (the dashboard; Secure cookies need TLS)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound (image pulls, TLS certificates, SES, SSM)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_eip" "server" {
  domain = "vpc"
}

resource "aws_eip_association" "server" {
  instance_id   = aws_instance.server.id
  allocation_id = aws_eip.server.id
}
