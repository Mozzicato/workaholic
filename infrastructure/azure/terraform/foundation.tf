# Stage 0 — guardrails. Created by bootstrap-stage-0-1.sh on 2026-09-17 and imported here.

import {
  to = azurerm_resource_group.main
  id = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

locals {
  budget_period = {
    start = "2026-09-01T00:00:00Z"
    end   = "2027-08-31T00:00:00Z"
  }
}

import {
  to = azurerm_consumption_budget_subscription.annual
  id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Consumption/budgets/workaholic-annual-budget"
}

resource "azurerm_consumption_budget_subscription" "annual" {
  name            = "workaholic-annual-budget"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 100
  time_grain      = "Annually"

  time_period {
    start_date = local.budget_period.start
    end_date   = local.budget_period.end
  }

  dynamic "notification" {
    for_each = [25, 50, 75, 90]
    content {
      enabled        = true
      operator       = "GreaterThanOrEqualTo"
      threshold      = notification.value
      threshold_type = "Actual"
      contact_emails = [var.alert_email]
    }
  }
}

import {
  to = azurerm_consumption_budget_subscription.monthly
  id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Consumption/budgets/workaholic-monthly-budget"
}

resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "workaholic-monthly-budget"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 20
  time_grain      = "Monthly"

  time_period {
    start_date = local.budget_period.start
    end_date   = local.budget_period.end
  }

  dynamic "notification" {
    for_each = [
      { threshold = 50, type = "Actual" },
      { threshold = 80, type = "Actual" },
      { threshold = 100, type = "Actual" },
      { threshold = 100, type = "Forecasted" },
    ]
    content {
      enabled        = true
      operator       = "GreaterThanOrEqualTo"
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      contact_emails = [var.alert_email]
    }
  }
}
