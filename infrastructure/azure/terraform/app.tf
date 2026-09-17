# Stage 2 — first deployment: database, registry, Container Apps, identities, logs.
# Approved 2026-09-17. See docs/architecture/azure-cost-plan.md for costs.

variable "deploy_app" {
  description = "Create the API app and migration job. Requires api_image to exist in the registry."
  type        = bool
  default     = false
}

locals {
  api_identity_name = "workaholic-api-id"
  database_name     = "workaholic"
}

# ── Logs ─────────────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "workaholic-prod-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  # Ingestion stops for the day at the cap: logs may be lost, spending cannot run away.
  daily_quota_gb = var.log_daily_quota_gb
  tags           = var.tags
}

# ── Images ───────────────────────────────────────────────────────────────────

resource "azurerm_container_registry" "main" {
  name                = var.container_registry_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.container_registry_sku
  admin_enabled       = false # pulls and pushes use Entra identities, never registry passwords
  tags                = var.tags
}

# ── Identities ───────────────────────────────────────────────────────────────

# The API, worker and migration job run as this identity. It holds no secret.
resource "azurerm_user_assigned_identity" "api" {
  name                = local.api_identity_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_role_assignment" "api_acr_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "api_ai_user" {
  scope                            = azurerm_cognitive_account.ai.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_user_assigned_identity.api.principal_id
  skip_service_principal_aad_check = true
}

# GitHub Actions deploys through OIDC federation: no Azure credential is stored in GitHub.
resource "azurerm_user_assigned_identity" "github_deploy" {
  name                = "workaholic-github-deploy-id"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "github_main" {
  name                      = "github-main-branch"
  user_assigned_identity_id = azurerm_user_assigned_identity.github_deploy.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = var.github_oidc_subject
}

resource "azurerm_role_assignment" "github_acr_push" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPush"
  principal_id                     = azurerm_user_assigned_identity.github_deploy.principal_id
  skip_service_principal_aad_check = true
}

# ── PostgreSQL (passwordless) ────────────────────────────────────────────────

resource "azurerm_postgresql_flexible_server" "main" {
  name                = var.postgres_server_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  version             = var.postgres_version
  sku_name            = var.postgres_sku
  storage_mb          = var.postgres_storage_mb
  auto_grow_enabled   = false # growth is a cost decision, not an automatic one

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  # Public endpoint restricted by firewall to Azure services; authentication is Entra-only.
  # Private networking (VNet) is the documented upgrade path.
  public_network_access_enabled = true

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = data.azurerm_client_config.current.tenant_id
  }

  tags = var.tags

  lifecycle {
    # Azure assigns a zone at creation; don't treat that as drift.
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = local.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  # 0.0.0.0 is Azure's convention for "allow connections from Azure services".
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "owner" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = data.azurerm_client_config.current.object_id
  # PostgreSQL role names are limited to 63 characters; Azure truncates longer guest UPNs.
  principal_name = substr(var.owner_principal_name, 0, 63)
  principal_type = "User"
}

# MVP simplification: the app identity is an Entra administrator so migrations can manage the
# schema without a manual SQL grant step. Tighten to a least-privilege role before launch.
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "api" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = azurerm_user_assigned_identity.api.principal_id
  principal_name      = azurerm_user_assigned_identity.api.name
  principal_type      = "ServicePrincipal"

  depends_on = [azurerm_postgresql_flexible_server_active_directory_administrator.owner]
}

# ── Container Apps ───────────────────────────────────────────────────────────

resource "azurerm_container_app_environment" "main" {
  name                       = "workaholic-prod-env"
  location                   = var.container_apps_location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  logs_destination           = "log-analytics"
  tags                       = var.tags

  # Serverless Consumption profile only: billed per use, no dedicated (hourly) profiles.
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

locals {
  # Shared by the API and the migration job. No secrets: every Azure dependency uses the
  # managed identity, and the only external value (Supabase URL) is public.
  runtime_env = {
    ENVIRONMENT     = "production"
    LOG_LEVEL       = "INFO"
    DATABASE_URL    = "postgresql+asyncpg://${local.api_identity_name}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${local.database_name}?ssl=require"
    DATABASE_AUTH   = "entra_id"
    AZURE_CLIENT_ID = azurerm_user_assigned_identity.api.client_id
  }
  api_env = merge(local.runtime_env, {
    CORS_ORIGINS        = join(",", var.cors_origins)
    SUPABASE_URL        = var.supabase_url
    AI_PROVIDER         = "azure"
    AZURE_AI_ENDPOINT   = "https://${var.ai_account_name}.openai.azure.com"
    AZURE_AI_MODEL      = var.ai_model
    AZURE_AI_AUTH       = "entra_id"
    AI_REASONING_EFFORT = var.ai_reasoning_effort
  })
}

resource "azurerm_container_app" "api" {
  count                        = var.deploy_app ? 1 : 0
  name                         = "workaholic-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = var.tags
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.api.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.api_min_replicas
    max_replicas = var.api_max_replicas

    container {
      name   = "api"
      image  = var.api_image
      cpu    = 0.25
      memory = "0.5Gi"

      dynamic "env" {
        for_each = local.api_env
        content {
          name  = env.key
          value = env.value
        }
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = 8000
      }
    }
  }

  lifecycle {
    ignore_changes = [
      # CI deploys new images; Terraform must not roll them back.
      template[0].container[0].image,
      # Managed by the Express environment, which normalises these to its own defaults.
      ingress[0].traffic_weight,
      template[0].cooldown_period_in_seconds,
      template[0].polling_interval_in_seconds,
      template[0].http_scale_rule,
      template[0].container[0].liveness_probe,
      template[0].container[0].readiness_probe,
    ]
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull,
    azurerm_role_assignment.api_ai_user,
    azurerm_postgresql_flexible_server_active_directory_administrator.api,
  ]
}

# The deploy identity may update only the API app.
resource "azurerm_role_assignment" "github_app_contributor" {
  count                            = var.deploy_app ? 1 : 0
  scope                            = azurerm_container_app.api[0].id
  role_definition_name             = "Container Apps Contributor"
  principal_id                     = azurerm_user_assigned_identity.github_deploy.principal_id
  skip_service_principal_aad_check = true
}

# ── Migrations ───────────────────────────────────────────────────────────────
# Azure created an Express environment for this subscription (France Central refused standard
# environments), and Express does not support Container Apps jobs. Migrations therefore run
# from GitHub Actions: the workflow opens a firewall rule for the runner's IP only for the
# duration of `alembic upgrade head`, authenticating with the deploy identity's Entra token.

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "github_deploy" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = azurerm_user_assigned_identity.github_deploy.principal_id
  principal_name      = azurerm_user_assigned_identity.github_deploy.name
  principal_type      = "ServicePrincipal"

  depends_on = [azurerm_postgresql_flexible_server_active_directory_administrator.api]
}

# Needed to add and remove the temporary firewall rule. Scoped to the database server only.
resource "azurerm_role_assignment" "github_postgres_firewall" {
  scope                            = azurerm_postgresql_flexible_server.main.id
  role_definition_name             = "Contributor"
  principal_id                     = azurerm_user_assigned_identity.github_deploy.principal_id
  skip_service_principal_aad_check = true
}
