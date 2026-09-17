# Azure infrastructure

Everything Workaholic runs in Azure. **Terraform in [`terraform/`](terraform/) is the source of
truth**; the portal is never the only record. Every resource was approved using the process in
[the cost plan](../../docs/architecture/azure-cost-plan.md).

Subscription: **Azure for Students** · Region: **France Central** (Container Apps: Germany West
Central) · Resource group: **workaholic-prod-rg**

Frontend: **https://workaholic-mauve.vercel.app** (Vercel, outside Azure). The API's
`CORS_ORIGINS` — set from `cors_origins` in `terraform.tfvars` — must list every browser origin
that calls it; Vercel preview URLs are not included.

## Inventory

| Stage | Resource | Type / SKU | Standing cost |
| --- | --- | --- | --- |
| 0 | `workaholic-prod-rg` | Resource group | $0 |
| 0 | `workaholic-annual-budget` | $100/year; email at 25/50/75/90% | $0 |
| 0 | `workaholic-monthly-budget` | $20/month; email at 50/80/100% actual, 100% forecast | $0 |
| 1 | `workaholic-ai-frc` | Foundry `AIServices` S0, key auth disabled | $0 (pay per token) |
| 1 | deployments `gpt-5-mini`, `gpt-4.1-mini` | Global Standard, 50K TPM each | $0 idle |
| 2 | `workaholic-prod-db` | PostgreSQL 17 Flexible, B1ms, 32 GB, Entra-only auth, 7-day backups | ≈ $18/mo running; storage only when stopped |
| 2 | `workaholicacr` | Container Registry Basic, admin user disabled | ≈ $5/mo |
| 2 | `workaholic-prod-env` | Container Apps **Express** environment (preview), Germany West Central | $0 fixed |
| 2 | `workaholic-api` | Container App, 0.25 vCPU / 0.5 GiB, scale 0–2 | Within free grant at low traffic |
| 2 | `workaholic-prod-logs` | Log Analytics, 30-day retention, 0.1 GB/day cap | $0 under 5 GB/month |
| 2 | `workaholic-api-id` | User-assigned identity: AcrPull, OpenAI User, PostgreSQL Entra admin | $0 |
| 2 | `workaholic-github-deploy-id` | OIDC-federated to `main`: AcrPush, API app contributor, PostgreSQL Entra admin + server contributor (temporary firewall rule for migrations) | $0 |

## Security model

- **No secrets in production.** The API authenticates to PostgreSQL, Foundry and the registry
  with its managed identity. The only external configuration (Supabase URL, CORS origins) is
  public.
- **PostgreSQL** accepts Microsoft Entra tokens only (password auth disabled). The public
  endpoint is limited by the "Allow Azure services" firewall rule.
  - *Known trade-offs, to revisit before launch:* the rule admits any Azure-hosted client (still
    requiring a valid Entra token), and the API identity is an Entra administrator so migrations
    need no manual grants. Upgrade path: VNet integration + a least-privilege database role.
- **GitHub Actions** deploys through OIDC federation limited to the `main` branch; no Azure
  credential is stored in GitHub.

## Using Terraform

```bash
az login
cd infrastructure/azure/terraform
cp terraform.tfvars.example terraform.tfvars   # fill in; values are not secret
terraform init
terraform plan -out=plan.tfplan                # always review: nothing may be replaced unexpectedly
terraform apply plan.tfplan
```

State is local (`terraform.tfstate`, gitignored) and contains no secrets. Moving it to a remote
backend is planned with Stage 3's storage account.

Deployment flow: CI passes on `main` → `.github/workflows/deploy-api.yml` builds the image, pushes
it to `workaholicacr`, runs `alembic upgrade head` from the runner (firewall opened for the
runner's IP only during that step), updates `workaholic-api`, then checks `/health` and `/ready`.
Terraform ignores image changes so it never rolls back a deploy.

### Why Express, and what it implies

Azure refused a standard Container Apps environment in France Central for this subscription
(`MaxNumberOfEnvironmentsInSubExceeded`) and created an **Express** environment in Germany West
Central. Express uses the same Consumption per-second pricing and free grant with no environment
fee, and scales to zero — but it is a **preview with no SLA**, doesn't support Container Apps
jobs (hence migrations from CI) or custom domains yet. Verified working on 2026-09-17: image pull
and PostgreSQL/AI access through the user-assigned managed identity.

Source: [Container Apps express FAQ](https://learn.microsoft.com/azure/container-apps/express-faq).

## Cost controls

- Stop the database when not testing (compute stops billing; Azure restarts it after 7 days):
  `az postgres flexible-server stop -g workaholic-prod-rg -n workaholic-prod-db`
  and `... start ...` when needed.
- API scales to zero; the first request after idle has a cold start.

## Quota findings (2026-09-17)

No Data Zone Standard quota for chat models; no quota for `gpt-5-nano`, `gpt-5.4-*`,
`gpt-5.6-*`. Deployed `gpt-5-mini` retires 2027-02-09 — the default model must move before then.

## History

`bootstrap-stage-0-1.sh` records the CLI commands that created Stages 0–1 before Terraform existed.
Those resources are now imported into Terraform; do not run the script again.
