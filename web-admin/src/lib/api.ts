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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = `请求失败：HTTP ${response.status}`;

    try {
      const body = await response.json();
      if (body.detail) {
        message = String(body.detail);
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