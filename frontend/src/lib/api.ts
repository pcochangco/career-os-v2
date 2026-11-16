import { Platform } from "react-native";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL ??
  (Platform.OS === "web" ? "/api/v1" : "http://localhost:8000/api/v1");

type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string | null;
};

export const SESSION_ENDED_MESSAGE = "Your session has ended. Please sign in again.";

let unauthorizedHandler: (() => void) | null = null;

/** Registered by the session provider: called when the API rejects the stored session. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId: string | null = null,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 401 && options.token) {
    // The stored session expired, was signed out elsewhere, or the account was deleted.
    // Clear it centrally so every screen returns to sign-in instead of showing a raw error.
    unauthorizedHandler?.();
    throw new ApiError(SESSION_ENDED_MESSAGE, 401, response.headers.get("X-Request-ID"));
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }>;
    } | null;
    const detail = payload?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail) && typeof detail[0]?.msg === "string"
        ? detail[0].msg.replace(/^Value error,\s*/i, "")
        : "Something went wrong. Please try again.";
    const requestId = response.headers.get("X-Request-ID");
    const displayMessage = response.status >= 500 && requestId
      ? `${message} Reference: ${requestId}.`
      : message;
    throw new ApiError(displayMessage, response.status, requestId);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
