# Stage 1 — Microsoft Foundry. Created by bootstrap-stage-0-1.sh on 2026-09-17 and imported here.

import {
  to = azurerm_cognitive_account.ai
  id = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}/providers/Microsoft.CognitiveServices/accounts/${var.ai_account_name}"
}

resource "azurerm_cognitive_account" "ai" {
  name                  = var.ai_account_name
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "AIServices"
  sku_name              = "S0"
  custom_subdomain_name = var.ai_account_name
  # Keyless: callers authenticate with Microsoft Entra ID only.
  local_auth_enabled = false
  # Created this way by the CLI; changing it would force Azure to recreate the resource.
  project_management_enabled = true
  tags                       = var.tags

  # Matches the existing resource (system-assigned identity, required for project management).
  identity {
    type = "SystemAssigned"
  }
}

import {
  for_each = var.ai_deployments
  to       = azurerm_cognitive_deployment.model[each.key]
  id       = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}/providers/Microsoft.CognitiveServices/accounts/${var.ai_account_name}/deployments/${each.key}"
}

resource "azurerm_cognitive_deployment" "model" {
  for_each             = var.ai_deployments
  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.ai.id

  model {
    format  = "OpenAI"
    name    = each.key
    version = each.value.version
  }

  # Pay-per-token; capacity limits throughput and therefore the maximum spend rate.
  sku {
    name     = "GlobalStandard"
    capacity = each.value.capacity
  }
}
