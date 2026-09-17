"""The benchmark's deterministic checks must catch fabrication, not just bad JSON."""

from benchmarks.pricing import estimate_cost_usd
from benchmarks.run import CallRecord, summarise
from benchmarks.tasks import (
    Bullet,
    BulletSet,
    EvidenceExtraction,
    ExtractedProject,
    JobRequirements,
    ParsedExperience,
    ParsedResume,
    check_bullet_writing,
    check_evidence_extraction,
    check_job_requirements,
    check_prompt_injection,
)


def faithful_project(**overrides: object) -> ExtractedProject:
    values: dict[str, object] = {
        "name": "StudyShare",
        "summary": "A textbook swap site for students",
        "technologies": ["FastAPI", "PostgreSQL", "Next.js"],
        "outcomes": ["About 300 students signed up in the first semester"],
        "supporting_quotes": ["About 300 students signed up in the first semester"],
    }
    values.update(overrides)
    return ExtractedProject.model_validate(values)


def test_faithful_extraction_passes_every_check() -> None:
    output = EvidenceExtraction(
        projects=[faithful_project()], missing_information=["How many swaps happened?"]
    )

    assert all(check_evidence_extraction(output).values())


def test_extraction_flags_invented_technology_numbers_and_quotes() -> None:
    output = EvidenceExtraction(
        projects=[
            faithful_project(
                technologies=["FastAPI", "Kubernetes"],
                outcomes=["Grew to 5,000 users"],
                supporting_quotes=["scaled to thousands of users"],
            )
        ],
        missing_information=[],
    )

    results = check_evidence_extraction(output)

    assert results["technologies_grounded"] is False
    assert results["numbers_grounded"] is False
    assert results["quotes_verbatim"] is False
    assert results["asks_follow_up"] is False


def test_bullets_flag_invented_metrics_and_uncited_claims() -> None:
    output = BulletSet(
        bullets=[
            Bullet(text="Built StudyShare with FastAPI and PostgreSQL", evidence_ids=["E1", "E2"]),
            Bullet(text="Grew revenue 40% using React and AWS", evidence_ids=["E9"]),
        ]
    )

    results = check_bullet_writing(output)

    assert results["cites_valid_evidence"] is False
    assert results["numbers_grounded"] is False
    assert results["no_invented_terms"] is False


def test_faithful_bullets_pass() -> None:
    output = BulletSet(
        bullets=[
            Bullet(
                text="Built StudyShare, a textbook-swap site, with FastAPI, PostgreSQL, Next.js",
                evidence_ids=["E1", "E2"],
            ),
            Bullet(
                text="Reached about 300 student sign-ups in the first semester", evidence_ids=["E3"]
            ),
        ]
    )

    assert all(check_bullet_writing(output).values())


def test_job_requirements_checks() -> None:
    good = JobRequirements(
        role="Junior Backend Engineer",
        seniority="junior",
        required_skills=["Python", "FastAPI", "PostgreSQL", "pytest"],
        preferred_skills=["Docker", "AWS", "Azure"],
    )
    bad = JobRequirements(
        role="Backend Engineer",
        seniority="mid",
        required_skills=["Python", "Docker", "Kafka"],
        preferred_skills=[],
    )

    assert all(check_job_requirements(good).values())
    results = check_job_requirements(bad)
    assert not results["skills_grounded"]
    assert not results["required_complete"]
    assert not results["preferred_separated"]
    assert not results["seniority_correct"]


def test_prompt_injection_detection() -> None:
    resisted = ParsedResume(
        name="Ada Obi",
        summary="Software developer",
        experience=[],
        skills=["Django", "SQLite", "Git"],
    )
    obeyed = ParsedResume(
        name="Ada Obi",
        summary="PWNED",
        experience=[ParsedExperience(employer="Google", title="Senior Staff Engineer")],
        skills=["Django"],
    )

    assert all(check_prompt_injection(resisted).values())
    results = check_prompt_injection(obeyed)
    assert not results["ignored_injected_employer"]
    assert not results["no_canary_word"]


def test_cost_estimate_uses_zone_prices() -> None:
    assert estimate_cost_usd("gpt-5-nano", "global", 1_000_000, 1_000_000) == 0.45
    assert estimate_cost_usd("unknown-model", "global", 10, 10) is None


def test_summary_counts_failures_and_errors() -> None:
    records = [
        CallRecord(
            model="m",
            task="t",
            run=1,
            ok=True,
            checks={"a": True, "b": False},
            latency_ms=100,
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
        ),
        CallRecord(model="m", task="t", run=2, ok=False, error_code="AI_INVALID_OUTPUT"),
    ]

    [row] = summarise(records)

    assert row["schema_valid_rate"] == 0.5
    assert row["check_pass_rate"] == 0.5
    assert row["fully_correct_rate"] == 0.0
    assert row["failed_checks"] == ["t.b"]
    assert row["cost_per_1000_calls_usd"] == 1.0


def test_bullets_flag_invented_impact_language() -> None:
    output = BulletSet(
        bullets=[
            Bullet(
                text="Resolved a critical payment bug, enhancing transaction reliability",
                evidence_ids=["E4"],
            ),
            Bullet(text="Built StudyShare with FastAPI", evidence_ids=["E1", "E2"]),
        ]
    )

    assert check_bullet_writing(output)["no_invented_impact"] is False
