"""Named OpenAI-compatible providers for development and benchmarking.

Verified against the live APIs on 2026-09-17 with a structured-output call on fictional data:
gemini (gemini-2.5-flash), groq (openai/gpt-oss-120b), openrouter
(nvidia/nemotron-3-super-120b-a12b:free). Mistral's endpoint and key were confirmed by listing
models, but the account allowed 0 requests/minute, so its request settings are unverified.

Production uses Azure; these providers' free tiers may use submitted data to improve their
services, so they must only ever receive fictional data.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

PresetName = Literal["gemini", "groq", "mistral", "openrouter"]


@dataclass(frozen=True, slots=True)
class ProviderPreset:
    base_url: str
    token_limit_param: Literal["max_completion_tokens", "max_tokens"] = "max_completion_tokens"  # noqa: S105
    structured_output_mode: Literal["json_schema", "json_object"] = "json_schema"
    supports_reasoning_effort: bool = False
    default_headers: Mapping[str, str] = field(default_factory=dict)


PRESETS: dict[PresetName, ProviderPreset] = {
    "gemini": ProviderPreset(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        supports_reasoning_effort=True,
    ),
    "groq": ProviderPreset(
        base_url="https://api.groq.com/openai/v1",
        supports_reasoning_effort=True,
    ),
    "mistral": ProviderPreset(
        base_url="https://api.mistral.ai/v1",
        token_limit_param="max_tokens",  # noqa: S106
    ),
    "openrouter": ProviderPreset(
        base_url="https://openrouter.ai/api/v1",
        default_headers={"X-Title": "Workaholic"},
    ),
}
