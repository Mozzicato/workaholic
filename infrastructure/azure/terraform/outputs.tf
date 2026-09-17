output "ai_endpoint" {
  value = "https://${var.ai_account_name}.openai.azure.com"
}

output "container_registry_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "api_url" {
  value = var.deploy_app ? "https://${azurerm_container_app.api[0].ingress[0].fqdn}" : null
}

output "github_deploy" {
  description = "Values for the GitHub repository variables used by the deploy workflow."
  value = {
    AZURE_CLIENT_ID       = azurerm_user_assigned_identity.github_deploy.client_id
    AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID = var.subscription_id
    AZURE_RESOURCE_GROUP  = azurerm_resource_group.main.name
    ACR_NAME              = azurerm_container_registry.main.name
  }
}
