const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: "same-origin", // la cookie de sesión (httpOnly) viaja solo hacia este mismo sitio
  });

  if (!response.ok) {
    const { detail, code } = await safeError(response);
    throw new ApiError(response.status, detail, code);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function safeError(response: Response): Promise<{ detail: string; code?: string }> {
  try {
    const data = await response.json();
    return {
      detail: typeof data?.detail === "string" ? data.detail : `Error ${response.status}`,
      code: typeof data?.code === "string" ? data.code : undefined,
    };
  } catch {
    return { detail: `Error ${response.status}` };
  }
}
