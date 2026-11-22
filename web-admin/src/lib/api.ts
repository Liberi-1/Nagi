const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL
  ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface HealthResponse {
  status: string;
  mysql: string;
  redis: string;
  context_fallback: string;
}

export interface Persona {
  id: number;
  name: string;
  content: string;
  is_active: boolean;
  updated_at: string;
}

export interface PersonaPayload {
  name: string;
  content: string;
}

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item?.msg === "string") {
          return item.msg;
        }
        return JSON.stringify(item);
      })
      .join("；");
  }

  return "请求失败";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `请求失败：HTTP ${response.status}`;

    try {
      const body = await response.json();
      if (body.detail) {
        message = formatErrorDetail(body.detail);
      }
    } catch {
      // 非 JSON 错误响应保留 HTTP 状态提示
    }

    throw new Error(message);
  }

  return await response.json() as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function getActivePersona(): Promise<Persona> {
  return request<Persona>("/api/personas/active");
}

export function updateActivePersona(
  payload: PersonaPayload,
): Promise<Persona> {
  return request<Persona>("/api/personas/active", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify(payload),
  });
}