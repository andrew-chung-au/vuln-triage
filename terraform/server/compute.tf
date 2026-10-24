# The one EC2 instance, its EBS data volume and daily snapshots
# (architecture.md § Deployment, A36). Both Compose projects (dev, prod) run on
# it behind Caddy. The latest Amazon Linux 2023 AMI is resolved from SSM.

data "aws_ssm_parameter" "al2023" {
  # VERIFY: this public parameter name for Amazon Linux 2023 x86_64.
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "server" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.server.name
  vpc_security_group_ids = [aws_security_group.server.id]

  # No key pair: access is SSM Session Manager only.
  user_data = file("${path.module}/user-data.sh")

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "vuln-triage-server"
  }
}

# Separate data volume for the Postgres data of both projects, snapshotted daily.
resource "aws_ebs_volume" "data" {
  availability_zone = aws_instance.server.availability_zone
  size              = var.data_volume_gb
  type              = "gp3"
  encrypted         = true
  tags = {
    Name = "vuln-triage-data"
  }
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.server.id
}

# Daily snapshots of the data volume via Data Lifecycle Manager.
# VERIFY: the DLM role and that the schedule targets the project tag.
data "aws_iam_policy_document" "dlm_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "vuln-triage-dlm"
  assume_role_policy = data.aws_iam_policy_document.dlm_assume.json
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

resource "aws_dlm_lifecycle_policy" "data" {
  description        = "Daily snapshots of the VulnTriage data volume"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]
    target_tags = {
      Name = "vuln-triage-data"
    }
    schedule {
      name = "daily"
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"]
      }
      retain_rule {
        count = 7
      }
    }
  }
}
