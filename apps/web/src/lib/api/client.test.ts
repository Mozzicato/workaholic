import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { createApiClient } from "./client";
import { ApiError, NETWORK_ERROR_MESSAGE } from "./errors";

const itemSchema = z.object({ id: z.string() });

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

function setup(options: {
  responses: Array<Response | Error>;
  token?: string | null;
  refreshed?: string | null;
}) {
  const fetchMock = vi.fn<typeof fetch>();
  for (const response of options.responses) {
    if (response instanceof Error) fetchMock.mockRejectedValueOnce(response);
    else fetchMock.mockResolvedValueOnce(response);
  }
  const refreshAccessToken = vi.fn(async () => options.refreshed ?? null);
  const client = createApiClient({
    baseUrl: "http://api.test/",
    getAccessToken: async () => (options.token === undefined ? "token-1" : options.token),
    refreshAccessToken,
    fetch: fetchMock,
  });
  return { client, fetchMock, refreshAccessToken };
}

async function captureError(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.catch((caught: unknown) => caught);
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

describe("createApiClient", () => {
  it("sends the access token and returns validated data", async () => {
    const { client, fetchMock } = setup({ responses: [jsonResponse(200, { id: "abc" })] });

    await expect(client.request("/api/v1/items", { schema: itemSchema })).resolves.toEqual({ id: "abc" });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/items");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token-1");
    expect(init?.credentials).toBe("omit");
  });

  it("serialises JSON bodies", async () => {
    const { client, fetchMock } = setup({ responses: [jsonResponse(200, { id: "new" })] });

    await client.request("/api/v1/items", { method: "POST", body: { title: "CV" }, schema: itemSchema });

    const init = fetchMock.mock.calls[0][1];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ title: "CV" }));
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
  });

  it("does not call the API when signed out", async () => {
    const { client, fetchMock } = setup({ responses: [], token: null });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error.status).toBe(401);
    expect(error.code).toBe("UNAUTHENTICATED");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refreshes an expired session once and retries", async () => {
    const { client, fetchMock, refreshAccessToken } = setup({
      responses: [
        jsonResponse(401, { error: { code: "SESSION_EXPIRED", message: "Expired", request_id: "req_1" } }),
        jsonResponse(200, { id: "abc" }),
      ],
      refreshed: "token-2",
    });

    await expect(client.request("/api/v1/items", { schema: itemSchema })).resolves.toEqual({ id: "abc" });

    expect(refreshAccessToken).toHaveBeenCalledTimes(1);
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("Authorization")).toBe("Bearer token-2");
  });

  it("surfaces the auth error when the refresh fails", async () => {
    const { client, fetchMock } = setup({
      responses: [jsonResponse(401, { error: { code: "SESSION_EXPIRED", message: "Expired", request_id: "req_1" } })],
      refreshed: null,
    });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error.code).toBe("SESSION_EXPIRED");
    expect(error.isAuthError).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("maps the backend error contract onto ApiError", async () => {
    const { client } = setup({
      responses: [
        jsonResponse(422, {
          error: {
            code: "VALIDATION_ERROR",
            message: "Some of the information provided isn't valid.",
            request_id: "req_42",
            details: [{ field: "body.title", issue: "Field required" }],
          },
        }),
      ],
    });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error).toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Some of the information provided isn't valid.",
      requestId: "req_42",
      details: [{ field: "body.title", issue: "Field required" }],
    });
  });

  it("never shows raw upstream error pages to users", async () => {
    const { client } = setup({
      responses: [new Response("<html>502 Bad Gateway nginx</html>", { status: 502, headers: { "X-Request-ID": "req_gw" } })],
    });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error.code).toBe("INTERNAL_ERROR");
    expect(error.message).not.toContain("nginx");
    expect(error.requestId).toBe("req_gw");
  });

  it("reports network failures with a friendly message", async () => {
    const { client } = setup({ responses: [new TypeError("Failed to fetch")] });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.message).toBe(NETWORK_ERROR_MESSAGE);
  });

  it("rejects responses that don't match the expected shape", async () => {
    const { client } = setup({ responses: [jsonResponse(200, { unexpected: true }, { "X-Request-ID": "req_7" })] });

    const error = await captureError(client.request("/api/v1/items", { schema: itemSchema }));

    expect(error.code).toBe("INVALID_RESPONSE");
    expect(error.requestId).toBe("req_7");
  });
});
