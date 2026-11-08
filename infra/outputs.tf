output "nameservers" {
  description = "Put these four at Fasthosts (Domain Names → nameservers)."
  value       = aws_route53_zone.main.name_servers
}

output "bucket" {
  description = "Where the site files go."
  value       = aws_s3_bucket.site.id
}

output "distribution_id" {
  description = "Used to clear the CloudFront cache after a deploy."
  value       = aws_cloudfront_distribution.site.id
}

output "url" {
  value = "https://${var.domain}"
}
