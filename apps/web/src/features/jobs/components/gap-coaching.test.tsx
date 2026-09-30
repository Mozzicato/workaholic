import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test/render";

import { GapCoaching } from "./gap-coaching";

const request = vi.fn();

vi.mock("@/lib/api/browser", () => ({ getApiClient: () => ({ request }) }));

const JOB_ID = "11111111-1111-4111-8111-111111111111";

const COACHING = {
  job_id: JOB_ID,
  gaps: [
    { skill: "Kubernetes", adjacent: ["docker", "docker compose"] },
    { skill: "Kafka", adjacent: [] },
  ],
  ideas: [
    {
      title: "Containerise something you have already built",
      covers: ["Docker", "Kubernetes"],
      summary: "Take a project you have finished and make it run anywhere with one command.",
      steps: ["Write a Dockerfile for it.", "Deploy it to a small cluster."],
    },
  ],
  caveat:
    "These are not on your resume and will not be added. A skill goes on it when you have used it.",
};

describe("GapCoaching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("says what is missing and that it will not be added", async () => {
    request.mockResolvedValue(COACHING);
    renderWithQueryClient(<GapCoaching jobId={JOB_ID} />);

    // Listed as a gap, and named again in what to say about it.
    expect(await screen.findAllByText("Kubernetes")).not.toHaveLength(0);
    expect(screen.getByText("Kafka")).toBeInTheDocument();
    expect(screen.getByText(/will not be added/)).toBeInTheDocument();
  });

  it("gives them the nearest true thing to say", async () => {
    request.mockResolvedValue(COACHING);
    renderWithQueryClient(<GapCoaching jobId={JOB_ID} />);

    expect(await screen.findByText("Say this in the interview")).toBeInTheDocument();
    expect(screen.getByText(/docker, docker compose/)).toBeInTheDocument();
  });

  it("gives them something finishable to build", async () => {
    request.mockResolvedValue(COACHING);
    renderWithQueryClient(<GapCoaching jobId={JOB_ID} />);

    expect(
      await screen.findByText("Containerise something you have already built"),
    ).toBeInTheDocument();
    expect(screen.getByText("Write a Dockerfile for it.")).toBeInTheDocument();
    expect(screen.getByText(/add it as a project with its repository link/)).toBeInTheDocument();
  });

  it("says so when there is no gap at all", async () => {
    request.mockResolvedValue({ ...COACHING, gaps: [], ideas: [] });
    renderWithQueryClient(<GapCoaching jobId={JOB_ID} />);

    expect(await screen.findByText("Nothing here you cannot back up")).toBeInTheDocument();
  });
});
