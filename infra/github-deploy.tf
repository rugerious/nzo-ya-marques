# GitHub Actions deploys the site with short-lived credentials (OIDC): no AWS keys stored in GitHub.

# Repositories created after mid-July 2026 send an immutable OIDC subject: owner and repo carry their numeric IDs.
# A deleted-and-recreated repo with the same name gets new IDs, so it cannot reuse this role.
# Check with: gh api repos/rugerious/nzo-ya-marques/actions/oidc/customization/sub
variable "github_repo_subject" {
  description = "Immutable OIDC subject prefix of the only repository allowed to deploy."
  type        = string
  default     = "rugerious@280082370/nzo-ya-marques@1450333058"
}

# The GitHub OIDC provider already exists in this account (shared with other projects), so it is read, not created.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only pushes to main in this repository: pull requests and forks cannot deploy.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo_subject}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "nzoyamarques-github-deploy"
  description          = "GitHub Actions deploy for nzoyamarques.com"
  assume_role_policy   = data.aws_iam_policy_document.deploy_trust.json
  max_session_duration = 3600
}

# Least privilege: write the site bucket and clear this one distribution's cache. Nothing else.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid       = "ListSiteBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.site.arn]
  }

  statement {
    sid       = "WriteSiteObjects"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
  }

  statement {
    sid       = "InvalidateCache"
    actions   = ["cloudfront:CreateInvalidation"]
    resources = [aws_cloudfront_distribution.site.arn]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "deploy-site"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}

output "deploy_role_arn" {
  description = "Role GitHub Actions assumes to deploy."
  value       = aws_iam_role.deploy.arn
}
