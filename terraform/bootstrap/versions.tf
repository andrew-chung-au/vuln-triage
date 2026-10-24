# VERIFY: the Terraform version the AWS provider needs; OpenTofu runs the same
# files. Pin a conservative floor and let the human's installed version satisfy it.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      project = "vuln-triage"
    }
  }
}
