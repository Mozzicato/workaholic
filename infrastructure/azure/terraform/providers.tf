provider "azurerm" {
  subscription_id = var.subscription_id

  # Terraform must never register resource providers it doesn't need; each is approved first.
  resource_provider_registrations = "none"

  features {
    resource_group {
      # Refuse to delete a resource group that still contains resources Terraform doesn't manage.
      prevent_deletion_if_contains_resources = true
    }
  }
}

data "azurerm_client_config" "current" {}
