#!/usr/bin/env bash
# Stage 0 (guardrails) and Stage 1 (AI) for Workaholic, as approved on 2026-09-17.
#
# This is the exact, re-runnable record of what was created from the CLI. It is a bootstrap
# until the Terraform configuration exists (AZURE.md §51); do not add resources here without
# the approval described in docs/architecture/azure-cost-plan.md.
#
# Usage: az login && SUBSCRIPTION_ID=... ALERT_EMAIL=... ./bootstrap-stage-0-1.sh
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash on Windows would otherwise rewrite /subscriptions/... paths

: "${SUBSCRIPTION_ID:?set SUBSCRIPTION_ID}"
: "${ALERT_EMAIL:?set ALERT_EMAIL}"

LOCATION="${LOCATION:-francecentral}"
RESOURCE_GROUP="${RESOURCE_GROUP:-workaholic-prod-rg}"
AI_ACCOUNT="${AI_ACCOUNT:-workaholic-ai-frc}"
TAGS=(project=workaholic environment=prod managedBy=cli-bootstrap)

az account set --subscription "$SUBSCRIPTION_ID"

# ── Stage 0: guardrails (no cost) ────────────────────────────────────────────
az provider register --namespace Microsoft.CognitiveServices --wait
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags "${TAGS[@]}" -o none

budget() {  # name amount grain notifications-json
  az rest --method put \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Consumption/budgets/$1?api-version=2023-05-01" \
    --body "{\"properties\":{\"category\":\"Cost\",\"amount\":$2,\"timeGrain\":\"$3\",
      \"timePeriod\":{\"startDate\":\"2026-09-01T00:00:00Z\",\"endDate\":\"2027-08-31T00:00:00Z\"},
      \"notifications\":$4}}" -o none
}
alert() {  # key threshold type
  printf '"%s":{"enabled":true,"operator":"GreaterThanOrEqualTo","threshold":%s,"contactEmails":["%s"],"thresholdType":"%s"}' \
    "$1" "$2" "$ALERT_EMAIL" "$3"
}
budget workaholic-annual-budget 100 Annually \
  "{$(alert actual_25 25 Actual),$(alert actual_50 50 Actual),$(alert actual_75 75 Actual),$(alert actual_90 90 Actual)}"
budget workaholic-monthly-budget 20 Monthly \
  "{$(alert actual_50 50 Actual),$(alert actual_80 80 Actual),$(alert actual_100 100 Actual),$(alert forecast_100 100 Forecasted)}"

# ── Stage 1: Microsoft Foundry (pay-per-token, no standing charge) ───────────
az cognitiveservices account create \
  --name "$AI_ACCOUNT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" \
  --kind AIServices --sku S0 --custom-domain "$AI_ACCOUNT" --tags "${TAGS[@]}" --yes -o none

AI_ID=$(az cognitiveservices account show -n "$AI_ACCOUNT" -g "$RESOURCE_GROUP" --query id -o tsv)

# Keyless only: callers must use Microsoft Entra ID.
az resource update --ids "$AI_ID" --set properties.disableLocalAuth=true -o none

# Only models sold by Azure with quota on this subscription (Global Standard; Data Zone quota is 0).
# Capacity is in thousands of tokens per minute and also bounds the maximum spend rate.
deploy() {  # name version
  az cognitiveservices account deployment create \
    -g "$RESOURCE_GROUP" -n "$AI_ACCOUNT" \
    --deployment-name "$1" --model-name "$1" --model-version "$2" --model-format OpenAI \
    --sku-name GlobalStandard --sku-capacity 50 -o none
}
deploy gpt-5-mini 2025-08-07
deploy gpt-4.1-mini 2025-04-14

# Local development and benchmarking with `az login` (no keys).
az role assignment create \
  --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User \
  --role "Cognitive Services OpenAI User" \
  --scope "$AI_ID" -o none

echo "Endpoint: https://$AI_ACCOUNT.openai.azure.com"
