# ADR-001 — Azure Container Apps for the backend

**Status:** Accepted · 2026-09-16

## Context

Workaholic needs to run a FastAPI API and Celery workers as separate processes, on an
Azure for Students budget ($100 credit). The team has no capacity to operate Kubernetes.

## Decision

Run the API and the worker as two Azure Container Apps in one Container Apps environment,
built from a single Docker image (`apps/api/Dockerfile`) with different start commands.
Images are built in CI and pushed to Azure Container Registry.

## Consequences

- Scale-to-zero and per-second billing keep idle cost low; cold starts are possible when
  minimum replicas is 0.
- No cluster to operate. AKS and VMs are explicitly out of scope for V1.
- The worker must not expose HTTP ingress.
