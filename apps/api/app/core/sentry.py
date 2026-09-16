import sentry_sdk

from app.core.config import Settings


def configure_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Resume data is sensitive: never attach request bodies, cookies or user details.
        send_default_pii=False,
        max_request_body_size="never",
    )
