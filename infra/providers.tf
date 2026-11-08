provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "nzo-ya-marques"
      ManagedBy = "terraform"
    }
  }
}

# CloudFront only accepts ACM certificates from us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "nzo-ya-marques"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
