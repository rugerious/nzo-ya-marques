# The domain stays registered at Fasthosts; only its nameservers point here.
resource "aws_route53_zone" "main" {
  name    = var.domain
  comment = "Nzo ya Marques"
}

locals {
  hostnames = {
    apex = var.domain
    www  = "www.${var.domain}"
  }

  # One A (IPv4) and one AAAA (IPv6) alias per hostname.
  alias_records = {
    for pair in setproduct(keys(local.hostnames), ["A", "AAAA"]) :
    "${pair[0]}-${pair[1]}" => { name = local.hostnames[pair[0]], type = pair[1] }
  }
}

resource "aws_route53_record" "site" {
  for_each = local.alias_records

  zone_id = aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
