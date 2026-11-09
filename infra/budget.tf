# Monthly cost alarm for this project only (resources tagged Project=nzo-ya-marques).
# Alert-only budgets are free. The email stays out of this public repo: set it in
# infra/terraform.tfvars (git-ignored), e.g.  alert_email = "you@example.com"

variable "alert_email" {
  description = "Where budget alerts go. Set in terraform.tfvars, never committed."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly limit for this project, in USD."
  type        = number
  default     = 5
}

resource "aws_budgets_budget" "monthly" {
  name         = "nzoyamarques-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:Project$nzo-ya-marques"]
  }

  # Real spend passes 80% of the limit.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # AWS forecasts the month will end above the limit.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
