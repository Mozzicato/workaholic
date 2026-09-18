import type { z } from "zod";

import { ApiError, apiErrorFromResponse, invalidResponseError, networkError } from "./errors";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export type RequestOptions<TSchema extends z.ZodType> = {
  method?: HttpMethod;
  body?: unknown;
  schema: TSchema;
  signal?: AbortSignal;
};

export type ApiClientConfig = {
  baseUrl: string;
  /** Current access token, or null when signed out. */
  getAccessToken: () => Promise<string | null>;
  /** Refresh the session and return the new access token, or null if that failed. */
  refreshAccessToken: () => Promise<string | null>;
  fetch?: typeof fetch;
};

export type ApiClient = {
  request<TSchema extends z.ZodType>(
    path: string,
    options: RequestOptions<TSchema>,
  ): Promise<z.infer<TSchema>>;
  /** An authenticated response, unparsed: for documents the API returns as HTML or PDF. */
  raw(path: string, options?: { signal?: AbortSignal }): Promise<Response>;
  /** A multipart POST, for the one thing the app sends that is not JSON: a recording. */
  upload<TSchema extends z.ZodType>(
    path: string,
    form: FormData,
    options: { schema: TSchema; signal?: AbortSignal },
  ): Promise<z.infer<TSchema>>;
};

/**
 * The only way the web app talks to the Workaholic API.
 * Attaches the user's access token, retries once after a session refresh, validates
 * every response against a schema, and turns failures into typed `ApiError`s.
 */
export function createApiClient(config: ApiClientConfig): ApiClient {
  const fetchImpl = config.fetch ?? fetch;
  const baseUrl = config.baseUrl.replace(/\/+$/, "");

  async function send(
    path: string,
    token: string,
    method: HttpMethod,
    body: unknown,
    signal?: AbortSignal,
  ) {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    const multipart = body instanceof FormData;
    // The browser sets multipart's Content-Type itself, including the boundary.
    if (body !== undefined && !multipart) headers["Content-Type"] = "application/json";
    try {
      return await fetchImpl(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
        signal,
        credentials: "omit",
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw networkError();
    }
  }

  /** Sends the request with a valid token, refreshing once if the first attempt is rejected. */
  async function authenticated(
    path: string,
    method: HttpMethod,
    body: unknown,
    signal?: AbortSignal,
  ): Promise<Response> {
    const token = await config.getAccessToken();
    if (!token) {
      throw new ApiError({
        status: 401,
        code: "UNAUTHENTICATED",
        message: "Please sign in to continue.",
      });
    }

    const response = await send(path, token, method, body, signal);
    if (response.status !== 401) return response;

    // Access tokens are short-lived; one refresh-and-retry covers normal expiry.
    const refreshed = await config.refreshAccessToken();
    return refreshed ? await send(path, refreshed, method, body, signal) : response;
  }

  return {
    async raw(path, options = {}) {
      const response = await authenticated(path, "GET", undefined, options.signal);
      if (!response.ok) throw await apiErrorFromResponse(response);
      return response;
    },

    async upload(path, form, { schema, signal }) {
      const response = await authenticated(path, "POST", form, signal);
      if (!response.ok) throw await apiErrorFromResponse(response);
      const requestId = response.headers.get("X-Request-ID");
      const parsed = schema.safeParse(await response.json().catch(() => undefined));
      if (!parsed.success) throw invalidResponseError(requestId);
      return parsed.data;
    },

    async request(path, { method = "GET", body, schema, signal }) {
      const response = await authenticated(path, method, body, signal);

      if (!response.ok) throw await apiErrorFromResponse(response);

      const requestId = response.headers.get("X-Request-ID");
      const payload: unknown =
        response.status === 204 ? null : await response.json().catch(() => undefined);
      const parsed = schema.safeParse(payload);
      if (!parsed.success) throw invalidResponseError(requestId);
      return parsed.data;
    },
  };
}
