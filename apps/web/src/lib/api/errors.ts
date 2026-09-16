import { z } from "zod";

/** Mirrors the backend's error contract: {"error": {"code", "message", "request_id"}} */
const apiErrorBodySchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().nullable(),
    details: z.array(z.object({ field: z.string(), issue: z.string() })).optional(),
  }),
});

export type ApiErrorDetail = { field: string; issue: string };

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: ApiErrorDetail[];

  constructor(options: {
    status: number;
    code: string;
    message: string;
    requestId?: string | null;
    details?: ApiErrorDetail[];
  }) {
    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId ?? null;
    this.details = options.details ?? [];
  }

  get isAuthError(): boolean {
    return this.status === 401;
  }
}

export const NETWORK_ERROR_MESSAGE =
  "We couldn't reach Workaholic. Check your connection and try again.";
const UNEXPECTED_ERROR_MESSAGE =
  "Something went wrong on our side. Your information is safe. Please try again.";

export async function apiErrorFromResponse(response: Response): Promise<ApiError> {
  const requestId = response.headers.get("X-Request-ID");
  try {
    const parsed = apiErrorBodySchema.safeParse(await response.json());
    if (parsed.success) {
      const { code, message, request_id, details } = parsed.data.error;
      return new ApiError({
        status: response.status,
        code,
        message,
        requestId: request_id ?? requestId,
        details,
      });
    }
  } catch {
    // Not JSON (e.g. a proxy error page) — fall through to a generic error.
  }
  return new ApiError({
    status: response.status,
    code: response.status >= 500 ? "INTERNAL_ERROR" : "UNEXPECTED_RESPONSE",
    message: UNEXPECTED_ERROR_MESSAGE,
    requestId,
  });
}

export function networkError(): ApiError {
  return new ApiError({ status: 0, code: "NETWORK_ERROR", message: NETWORK_ERROR_MESSAGE });
}

export function invalidResponseError(requestId: string | null): ApiError {
  return new ApiError({
    status: 0,
    code: "INVALID_RESPONSE",
    message: UNEXPECTED_ERROR_MESSAGE,
    requestId,
  });
}

/** A user-facing message for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return UNEXPECTED_ERROR_MESSAGE;
}
