# State bucket (aws-setup.md step 7; architecture.md § Deployment).
#
# One S3 bucket holding Terraform state: versioned, private, encrypted. Created
# once by the human with LOCAL state, then the state is moved into the bucket
# (see README-state.md). VERIFY: S3-native state locking (no DynamoDB table) is
# available in the Terraform version used; if not, add a lock table here.

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name
}

# Versioned, so a bad apply can be rolled back and teardown removes all versions.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypted at rest (SSE-S3; VERIFY: whether a KMS key is wanted instead).
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Private: block all public access.
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
