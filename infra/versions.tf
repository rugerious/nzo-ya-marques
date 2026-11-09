terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.70.0" # released 26 Aug 2026, pinned on purpose
    }
  }

  # The bucket name is passed at init time so the account ID stays out of this public repo:
  #   terraform init -backend-config="bucket=nzoyamarques-tfstate-<account-id>"
  backend "s3" {
    key          = "site/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true # native S3 locking, no DynamoDB table needed
  }
}
