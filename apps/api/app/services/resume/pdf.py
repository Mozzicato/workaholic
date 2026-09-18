"""HTML to PDF (PRD §21).

A browser is expensive to start, so one is launched with the application and shared. Each
render gets a fresh page in its own context, which is closed afterwards: one document's content
can never be visible to another's.

The page is given HTML directly rather than a URL, and navigation is not possible from it — a
resume is the user's own text, and this process holds a managed identity, so the renderer is
never allowed to fetch anything.
"""

import asyncio
from types import TracebackType

import structlog
from playwright.async_api import Browser, Playwright, async_playwright

from app.core.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)

PDF_TIMEOUT_MS = 20_000

MAX_CONCURRENT_RENDERS = 2
"""One render peaks around 170 MiB above the idle process. Two fit the container's 0.5 GiB with
room to spare; more would risk the whole app being killed to print a page."""


class PdfUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.SERVICE_UNAVAILABLE,
            "We couldn't produce the PDF just now. Your resume is saved — please try again.",
            503,
        )


class PdfRenderer:
    """A shared headless browser. Started with the app, stopped with it."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(MAX_CONCURRENT_RENDERS)

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            # The headless shell, explicitly: it prints the same PDF as full Chromium for a
            # third of the image size, which is what a container pulls on every cold start.
            channel="chromium-headless-shell",
            args=["--disable-dev-shm-usage"],  # /dev/shm is tiny in a container
        )
        logger.info("pdf.renderer.started", version=self._browser.version)

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def render(self, html: str) -> bytes:
        """The PDF for this HTML. A4, background graphics on, no browser headers or footers.

        Renders are capped: a queued request waits rather than pushing the container over its
        memory limit, which would take the API down with it.
        """
        async with self._slots:
            return await self._render(html)

    async def _render(self, html: str) -> bytes:
        browser = await self._ensure_browser()
        context = await browser.new_context()
        try:
            page = await context.new_page()
            # The document is self-contained; nothing may be fetched while rendering it.
            await page.route("**/*", lambda route: asyncio.ensure_future(route.abort()))
            await page.set_content(html, wait_until="load", timeout=PDF_TIMEOUT_MS)
            return await page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=False,
                prefer_css_page_size=True,
            )
        except Exception as exc:
            logger.warning("pdf.render.failed", error=type(exc).__name__)
            raise PdfUnavailableError() from exc
        finally:
            await context.close()

    async def _ensure_browser(self) -> Browser:
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        # The browser died (it is a separate process): bring one back rather than fail every
        # later request. Serialised so a burst of requests starts exactly one.
        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            logger.warning("pdf.renderer.restarting")
            await self.stop()
            try:
                await self.start()
            except Exception as exc:
                raise PdfUnavailableError() from exc
            if self._browser is None:  # pragma: no cover - start() sets it or raises
                raise PdfUnavailableError()
            return self._browser

    async def __aenter__(self) -> "PdfRenderer":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.stop()
