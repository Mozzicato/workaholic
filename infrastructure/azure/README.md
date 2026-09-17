# Azure infrastructure

Current inventory of everything Workaholic has created in Azure. Every resource here was approved
using the process in [the cost plan](../../docs/architecture/azure-cost-plan.md).

Subscription: **Azure for Students** · Region: **France Central** · Resource group:
**workaholic-prod-rg**

| Stage | Resource | Type / SKU | Standing cost | Created |
| --- | --- | --- | --- | --- |
| 0 | `Microsoft.CognitiveServices` provider registration | — | $0 | 2026-09-17 |
| 0 | `workaholic-prod-rg` | Resource group | $0 | 2026-09-17 |
| 0 | `workaholic-annual-budget` | Budget $100/year; email at 25/50/75/90% actual | $0 | 2026-09-17 |
| 0 | `workaholic-monthly-budget` | Budget $20/month; email at 50/80/100% actual and 100% forecast | $0 | 2026-09-17 |
| 1 | `workaholic-ai-frc` | Microsoft Foundry (`AIServices`, S0), key auth **disabled** | $0 (pay per token) | 2026-09-17 |
| 1 | deployment `gpt-5-mini` (2025-08-07) | Global Standard, 50K TPM | $0 idle | 2026-09-17 |
| 1 | deployment `gpt-4.1-mini` (2025-04-14) | Global Standard, 50K TPM | $0 idle | 2026-09-17 |
| 1 | Role *Cognitive Services OpenAI User* → account owner | RBAC on `workaholic-ai-frc` | $0 | 2026-09-17 |

AI endpoint: `https://workaholic-ai-frc.openai.azure.com` (Entra ID only).

## Reproducing

`bootstrap-stage-0-1.sh` is the exact record of the CLI commands used. It will be replaced by
Terraform before Stage 2; until then, change infrastructure only through that script (or its
successor) so the portal is never the only source of truth.

## Quota findings (2026-09-17)

The subscription has **no Data Zone Standard quota** for chat models and no quota for
`gpt-5-nano`, `gpt-5.4-*` or `gpt-5.6-*`. Chat models sold by Azure with quota: `gpt-5-mini`
(500), `gpt-4.1-mini` (200), `o4-mini` (100, retiring 2026-11-19). Microsoft's
[quota request form](https://aka.ms/oai/stuquotarequest) can be used to ask for more; priority
goes to subscriptions that use their existing quota.

Model retirement dates for the deployed versions: `gpt-5-mini` 2027-02-09, `gpt-4.1-mini`
2027-04-14. The default model must be revisited before those dates.

## Tear-down

Deleting the resource group removes Stage 1 resources:
`az group delete --name workaholic-prod-rg`. Budgets live at subscription scope and are removed
separately.
