"""Microsoft Entra ID credentials shared by every Azure dependency (AI, PostgreSQL)."""

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential


def create_azure_credential(*, production: bool, client_id: str | None) -> AsyncTokenCredential:
    """Production: only the app's user-assigned managed identity, never a developer login.
    Development: `DefaultAzureCredential`, which picks up `az login`."""
    if production:
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)
