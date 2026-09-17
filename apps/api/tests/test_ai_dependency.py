from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.api.deps import get_llm
from app.services.ai.base import LLMProvider
from tests.conftest import AppFactory, running


def add_ai_route(app: FastAPI) -> None:
    @app.get("/test/ai")
    async def uses_ai(llm: Annotated[LLMProvider, Depends(get_llm)]) -> dict[str, str]:
        return {"provider": llm.name}


@pytest.mark.usefixtures("db_engine")
async def test_ai_endpoints_fail_clearly_when_ai_is_disabled(make_app: AppFactory) -> None:
    app = make_app(ai_provider="disabled")
    add_ai_route(app)

    async with running(app) as client:
        response: httpx.Response = await client.get("/test/ai")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"
