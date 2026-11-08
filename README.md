# Nzo ya Marques

*"The house of the Marques" in Kikongo.* The personal site of Paulo Martinho: fifteen years of mobile networks (2G→5G, RAN, submarine cables, data centres), now moving to cloud.

Live at **[nzoyamarques.com](https://nzoyamarques.com)**.

## What this repository shows

A static site run the way a production service would be:

| Layer | Service | Status |
|---|---|---|
| Content | Static HTML in `site/` | ✅ |
| Hosting | S3 (private) + CloudFront with Origin Access Control | ✅ |
| TLS | ACM certificate, DNS-validated | ✅ |
| DNS | Route 53 hosted zone (domain registered at Fasthosts) | ✅ |
| Infrastructure as code | Terraform, remote state in S3 | ✅ |
| Delivery | GitHub Actions with OIDC to AWS: no stored keys | 🔜 |

## Layout

```
site/        the website
infra/       Terraform
.github/     CI and deploy workflows (coming next)
```

## How changes ship

Branch → pull request → CI → merge → automatic deploy. No secrets in Git.

## Roadmap

1. Repository and README ✅
2. Terraform: S3, CloudFront, ACM, Route 53 ✅ ← *live*
3. GitHub Actions deploy with OIDC
4. Content refresh: Terraform, current projects, a link to the family room (Kuribotas)
5. Optional: a private weekly briefing (kept out of this public repo)
