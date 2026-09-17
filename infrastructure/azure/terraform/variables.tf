# Cost-relevant settings are variables so they can be changed without editing resources.
# Defaults are the approved, smallest practical configuration (docs/architecture/azure-cost-plan.md).

variable "subscription_id" {
  description = "Azure for Students subscription ID."
  type        = string
}

variable "location" {
  description = "Region allowed by the subscription policy."
  type        = string
  default     = "francecentral"
}

variable "container_apps_location" {
  description = <<-EOT
    Region for the Container Apps environment. Azure refused environment creation in
    francecentral for this subscription (MaxNumberOfEnvironmentsInSubExceeded, 2026-09-17), so the
    nearest allowed region is used; PostgreSQL stays in var.location.
  EOT
  type        = string
  default     = "germanywestcentral"
}

variable "resource_group_name" {
  type    = string
  default = "workaholic-prod-rg"
}

variable "alert_email" {
  description = "Where budget alerts are sent."
  type        = string
}

variable "owner_principal_name" {
  description = "Entra user principal name of the owner, made a PostgreSQL Entra administrator."
  type        = string
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy through OIDC."
  type        = string
  default     = "Mozzicato/workaholic"
}

# ── AI (Stage 1) ─────────────────────────────────────────────────────────────

variable "ai_account_name" {
  type    = string
  default = "workaholic-ai-frc"
}

variable "ai_deployments" {
  description = "Pay-per-token model deployments. Capacity is thousands of tokens per minute."
  type = map(object({
    version  = string
    capacity = number
  }))
  default = {
    "gpt-5-mini"   = { version = "2025-08-07", capacity = 50 }
    "gpt-4.1-mini" = { version = "2025-04-14", capacity = 50 }
  }
}

variable "ai_model" {
  description = "Deployment the API uses by default (chosen by benchmark)."
  type        = string
  default     = "gpt-5-mini"
}

variable "ai_reasoning_effort" {
  type    = string
  default = "low"
}

# ── Application (Stage 2) ────────────────────────────────────────────────────

variable "container_registry_name" {
  type    = string
  default = "workaholicacr"
}

variable "postgres_server_name" {
  type    = string
  default = "workaholic-prod-db"
}

variable "postgres_sku" {
  description = "Burstable B1ms is the smallest SKU (~$13.87/month compute when running)."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "Smallest size. Storage can grow later but never shrink."
  type        = number
  default     = 32768
}

variable "postgres_version" {
  type    = string
  default = "17"
}

variable "log_daily_quota_gb" {
  description = "Hard daily ingestion cap; 0.1 GB/day stays under the 5 GB/month free tier."
  type        = number
  default     = 0.1
}

variable "api_image" {
  description = "Initial API image. CI owns the image after creation (ignored by Terraform)."
  type        = string
}

variable "api_min_replicas" {
  description = "0 = scale to zero (no charge while idle; first request has a cold start)."
  type        = number
  default     = 0
}

variable "api_max_replicas" {
  type    = number
  default = 2
}

variable "cors_origins" {
  description = "Browser origins allowed to call the API."
  type        = list(string)
}

variable "supabase_url" {
  type = string
}

variable "tags" {
  type = map(string)
  default = {
    project     = "workaholic"
    environment = "prod"
    managedBy   = "terraform"
  }
}
