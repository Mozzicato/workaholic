"""Voice, which is an interface over the interview and nothing more (PRD §26).

The things that matter: a recording is transcribed and discarded, nothing is recorded against
the interview until the person sends the text, one account cannot transcribe into another's
interview, and turning voice off leaves the interview working.
"""

import uuid
from typing import Any

import pytest
from fastapi import FastAPI

from app.api.deps import get_speech
from app.services.speech import Audio, Transcription
from app.services.speech.errors import SpeechUnavailableError
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running
from tests.test_interview import Scripted, facts, start
from tests.test_resume_generation import app_with, sign_in

INTERVIEWS = "/api/v1/interviews"
WEBM = b"\x1a\x45\xdf\xa3fake-webm-audio"


class FakeSpeech:
    """A provider that returns a fixed transcript, and remembers what it was handed."""

    def __init__(self, text: str = "i interned at lumen freight in 2025", fail: bool = False):
        self._text = text
        self._fail = fail
        self.received: list[Audio] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-transcribe"

    async def transcribe(self, audio: Audio, *, language: str | None = None) -> Transcription:
        self.received.append(audio)
        if self._fail:
            raise SpeechUnavailableError()
        return Transcription(text=self._text, model=self.model, provider=self.name, latency_ms=1.0)

    async def aclose(self) -> None:
        return None


def app_with_voice(llm: Scripted, speech: FakeSpeech, make_app: AppFactory) -> FastAPI:
    app = app_with(llm, make_app)
    app.dependency_overrides[get_speech] = lambda: speech
    return app


def recording(content: bytes = WEBM, content_type: str = "audio/webm") -> dict[str, Any]:
    return {"audio": ("answer.webm", content, content_type)}


@pytest.mark.usefixtures("db_engine")
class TestTranscribing:
    async def test_a_recording_comes_back_as_text(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files=recording(),
            )

        assert response.status_code == 200
        assert response.json() == {"text": "i interned at lumen freight in 2025"}
        assert speech.received[0].content == WEBM

    async def test_transcribing_records_nothing_until_the_answer_is_sent(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """The person must see what was heard before it becomes part of their record."""
        speech = FakeSpeech()
        llm = Scripted(facts(employer="Lumen Freight", title="Intern"))
        async with running(app_with_voice(llm, speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)
            interview_id = started["session"]["id"]

            await client.post(
                f"{INTERVIEWS}/{interview_id}/transcriptions", headers=headers, files=recording()
            )
            transcript = await client.get(f"{INTERVIEWS}/{interview_id}", headers=headers)
            profile = await client.get("/api/v1/profile", headers=headers)

        assert len(transcript.json()["messages"]) == 1, "only the opening question so far"
        assert profile.json()["experience"] == []
        assert llm.calls == [], "no extraction happens from a transcription alone"

    async def test_the_transcript_then_goes_through_the_ordinary_answer_path(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        llm = Scripted(facts(employer="Lumen Freight", title="Intern"))
        async with running(app_with_voice(llm, speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)
            interview_id = started["session"]["id"]

            heard = await client.post(
                f"{INTERVIEWS}/{interview_id}/transcriptions", headers=headers, files=recording()
            )
            sent = await client.post(
                f"{INTERVIEWS}/{interview_id}/answers",
                headers=headers,
                json={"text": heard.json()["text"]},
            )
            profile = await client.get("/api/v1/profile", headers=headers)

        assert sent.status_code == 201
        # "Intern" is not in "i interned at lumen freight", so the title is not recorded from it:
        # the record holds the employer and waits to be told the rest.
        assert sent.json()["recorded"] == ["Lumen Freight"]
        role = profile.json()["experience"][0]
        assert role["employer"] == "Lumen Freight"
        assert role["title"] is None

    async def test_an_edited_transcript_is_what_gets_recorded(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """Speech recognition mishears names; the person's correction is what counts."""
        speech = FakeSpeech(text="i interned at loomin freight")
        llm = Scripted(facts(employer="Lumen Freight", title="Intern"))
        async with running(app_with_voice(llm, speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files=recording(),
            )
            sent = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/answers",
                headers=headers,
                json={"text": "i interned at Lumen Freight as an Intern"},
            )

        assert sent.json()["recorded"] == ["Intern at Lumen Freight"]


@pytest.mark.usefixtures("db_engine")
class TestWhatIsRefused:
    @pytest.mark.parametrize(
        "content_type", ["application/pdf", "text/plain", "application/octet-stream", ""]
    )
    async def test_a_file_that_is_not_audio(
        self, make_app: AppFactory, idp: FakeIdentityProvider, content_type: str
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files={"audio": ("answer.pdf", b"%PDF-1.4", content_type)},
            )

        assert response.status_code == 422
        assert speech.received == [], "nothing unsupported reaches the provider"

    async def test_an_empty_recording(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files=recording(content=b""),
            )

        assert response.status_code == 422
        assert speech.received == []

    async def test_a_recording_that_is_too_long(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files=recording(content=b"0" * (10 * 1024 * 1024 + 1)),
            )

        assert response.status_code == 422
        assert speech.received == []

    async def test_a_provider_failure_tells_the_user_to_type_instead(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech(fail=True)
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=headers,
                files=recording(),
            )

        assert response.status_code == 503
        assert "type your answer" in response.json()["error"]["message"]


@pytest.mark.usefixtures("db_engine")
class TestVoiceOffAndOwnership:
    async def test_voice_off_leaves_the_interview_working(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = Scripted(facts(employer="Lumen Freight", title="Intern"))
        app = app_with(llm, make_app)  # no speech provider configured
        async with running(app) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)
            interview_id = started["session"]["id"]

            voice = await client.post(
                f"{INTERVIEWS}/{interview_id}/transcriptions", headers=headers, files=recording()
            )
            typed = await client.post(
                f"{INTERVIEWS}/{interview_id}/answers",
                headers=headers,
                json={"text": "I was an Intern at Lumen Freight"},
            )

        assert voice.status_code == 503
        assert "type your answer" in voice.json()["error"]["message"]
        assert typed.status_code == 201

    async def test_another_account_cannot_transcribe_into_this_interview(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            owner = await sign_in(client, idp)
            started = await start(client, owner)

            intruder = bearer(idp.token(subject=str(uuid.uuid4()), email="eve@example.com"))
            await client.get("/api/v1/me", headers=intruder)
            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions",
                headers=intruder,
                files=recording(),
            )

        assert response.status_code == 404
        assert speech.received == [], "ownership is checked before any audio is sent anywhere"

    async def test_transcribing_requires_signing_in(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        speech = FakeSpeech()
        async with running(app_with_voice(Scripted(), speech, make_app)) as client:
            headers = await sign_in(client, idp)
            started = await start(client, headers)

            response = await client.post(
                f"{INTERVIEWS}/{started['session']['id']}/transcriptions", files=recording()
            )

        assert response.status_code == 401
        assert speech.received == []
