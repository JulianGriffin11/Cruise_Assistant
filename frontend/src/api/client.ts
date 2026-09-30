import { apiBaseUrl } from "@/lib/env";

export type Cruise = {
  id: string;
  name: string;
  year: number;
  start_date: string | null;
  end_date: string | null;
};

export type CruiseCreate = {
  name: string;
  year: number;
  start_date: string | null;
  end_date: string | null;
};

export type Document = {
  id: string;
  cruise_id: string;
  filename: string;
  page_count: number | null;
  status: "processing" | "ready" | "failed";
  error_message: string | null;
};

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type Citation = {
  cruise: string;
  year: number;
  page: number;
};

type StreamCallbacks = {
  onToken: (token: string) => void;
  onCitations: (citations: Citation[]) => void;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, options);
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export function listCruises(): Promise<Cruise[]> {
  return request("/cruises");
}

export function createCruise(body: CruiseCreate): Promise<Cruise> {
  return request("/cruises", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listDocuments(): Promise<Document[]> {
  return request("/documents");
}

export function uploadDocument(
  cruiseId: string,
  file: File,
): Promise<Document> {
  const body = new FormData();
  body.set("cruise_id", cruiseId);
  body.set("file", file);
  return request("/documents", { method: "POST", body });
}

export function retryDocument(documentId: string): Promise<Document> {
  return request(`/documents/${documentId}/retry`, { method: "POST" });
}

export async function streamChat(
  message: string,
  cruiseId: string | null,
  history: ChatTurn[],
  callbacks: StreamCallbacks,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      cruise_id: cruiseId,
      history,
    }),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  if (!response.body) {
    throw new Error("The response stream was unavailable.");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += value ?? "";
    const events = buffer.replaceAll("\r\n", "\n").split("\n\n");
    buffer = events.pop() ?? "";
    for (const event of events) {
      dispatchStreamEvent(event, callbacks);
    }
    if (done) {
      if (buffer.trim()) {
        dispatchStreamEvent(buffer, callbacks);
      }
      break;
    }
  }
}

function dispatchStreamEvent(eventBlock: string, callbacks: StreamCallbacks) {
  const lines = eventBlock.split("\n");
  const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!event || !data) {
    return;
  }
  if (event === "token") {
    callbacks.onToken(JSON.parse(data) as string);
  } else if (event === "citations") {
    callbacks.onCitations(JSON.parse(data) as Citation[]);
  }
}
