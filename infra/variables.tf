variable "domain" {
  description = "Apex domain of the site (registered at Fasthosts, DNS served by Route 53)."
  type        = string
  default     = "nzoyamarques.com"
}

variable "region" {
  description = "Home region for the bucket and the Terraform state."
  type        = string
  default     = "eu-west-2"
}
