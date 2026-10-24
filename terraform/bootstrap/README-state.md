# Moving state into the bucket (the human, once)

The bootstrap module is applied with **local** state (the bucket doesn't exist
yet), then its state is migrated into the bucket it just created.

1. `cd terraform/bootstrap`
2. `cp terraform.tfvars.example terraform.tfvars` and set a globally unique
   `state_bucket_name`.
3. `terraform init` (local state) → `terraform apply`.
4. Add this backend block to `versions.tf` (or a `backend.tf`), using the bucket
   from step 2 and your region:

   ```hcl
   terraform {
     backend "s3" {
       bucket  = "vuln-triage-tfstate-..."   # your state_bucket_name
       key     = "bootstrap/terraform.tfstate"
       region  = "ap-southeast-2"
       encrypt = true
       # VERIFY: S3-native state locking (use_lockfile) in your Terraform
       # version; if unavailable, add a DynamoDB lock table and `dynamodb_table`.
     }
   }
   ```
5. `terraform init` again and accept the prompt to copy existing state to the new
   backend (`VERIFY:` the exact migrate prompt wording).

The `deploy-roles/` and `server/` modules use the same backend `s3` block with
their own `key` (`deploy-roles/terraform.tfstate`, `server/terraform.tfstate`).
