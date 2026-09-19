"""Render every resume template with the same sample student, as PDF and as preview images.

    uv run --with pypdfium2 --with pillow python scripts/render_template_previews.py [output-dir]

The images are the thumbnails in the template gallery (apps/web/public/templates). Each is the
first page of a real PDF, printed by the same Chromium from the same HTML as a download, so a
thumbnail can only show what a download would. Run this after changing any template and commit
the images. pypdfium2 and Pillow are only needed here, which is why they are not dependencies.

The sample person is invented and is labelled as an example wherever it is shown.
"""

import asyncio
import sys
from pathlib import Path

import pypdfium2  # type: ignore[import-not-found]
from playwright.async_api import async_playwright

from app.models.candidate import ResumeTemplate
from app.schemas.resume_document import (
    Bullet,
    ResumeBasics,
    ResumeCertification,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeProject,
    ResumeSkillGroup,
)
from app.services.resume.rendering import render_html

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "web" / "public" / "templates"


def _bullets(item_id: str, *lines: str) -> list[Bullet]:
    return [
        Bullet(text=line, source_item_id=item_id, source_bullet_index=index)
        for index, line in enumerate(lines)
    ]


SAMPLE = ResumeDocument(
    basics=ResumeBasics(
        full_name="Amara Okafor",
        email="amara.okafor@example.com",
        phone="+234 800 000 0000",
        location="Lagos, Nigeria",
        links=[ResumeLink(label="Github", url="https://github.com/amara-example")],
    ),
    experience=[
        ResumeExperience(
            item_id="role-1",
            employer="Northwind Logistics",
            title="Software Engineering Intern",
            location="Lagos",
            start_date="2025-06",
            end_date="2025-09",
            bullets=_bullets(
                "role-1",
                "Changed the invoice import job to read large files in chunks, so it stopped "
                "failing on month-end uploads",
                "Wrote the first automated tests for the pricing module",
                "Documented the deployment steps the team now follows for releases",
            ),
            technologies=["Python", "PostgreSQL", "Docker"],
        ),
        ResumeExperience(
            item_id="role-2",
            employer="Department of Computer Science",
            title="Student Lab Assistant",
            location="Lagos",
            start_date="2024-01",
            end_date="2024-12",
            bullets=_bullets(
                "role-2",
                "Helped first-year students debug their programming assignments each week",
            ),
        ),
    ],
    education=[
        ResumeEducation(
            item_id="edu-1",
            institution="University of Lagos",
            qualification="BSc",
            field_of_study="Computer Science",
            grade="4.52/5",
            start_date="2022",
            end_date="2026",
        )
    ],
    projects=[
        ResumeProject(
            item_id="project-1",
            name="Campus Shuttle Tracker",
            url="https://github.com/amara-example/shuttle",
            bullets=_bullets(
                "project-1",
                "Built a mobile app that shows where the campus shuttle is in real time",
                "About 200 students used it in its first month",
            ),
            technologies=["React Native", "Firebase"],
        ),
        ResumeProject(
            item_id="project-2",
            name="Course Timetable Planner",
            bullets=_bullets(
                "project-2", "A web page that finds clash-free timetables from a course list"
            ),
            technologies=["TypeScript", "Next.js"],
        ),
    ],
    skills=[
        ResumeSkillGroup(category="Languages", skills=["Python", "TypeScript", "SQL"]),
        ResumeSkillGroup(category="Tools", skills=["Git", "Docker", "PostgreSQL", "Figma"]),
    ],
    certifications=[
        ResumeCertification(
            item_id="cert-1", name="Microsoft Azure Fundamentals (AZ-900)", issued_date="2025-04"
        )
    ],
)


async def main(output: Path) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chromium-headless-shell")
        page = await browser.new_page()
        for template in ResumeTemplate:
            await page.set_content(render_html(SAMPLE, template), wait_until="load")
            pdf = await page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
            first_page = pypdfium2.PdfDocument(pdf)[0]
            # 1.3x the PDF's 72 dpi: sharp in the gallery on a phone, light on mobile data.
            image = first_page.render(scale=1.3).to_pil()
            target = output / f"{template.value}.webp"
            image.save(target, quality=82, method=6)
            print(f"{template.value}: {target} ({target.stat().st_size // 1024} KB)")
        await browser.close()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    target.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(target))
