const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type Status =
  | "answered" | "not_found" | "refer" | "personal" | "advice" | "off_topic" | "greeting" | "error";

export interface Source {
  url: string;
  title: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: Status;
  sources: Source[];
}

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

interface ChatResponse {
  conversation_id: string;
  answer: string;
  status: Status;
  sources: Source[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const sendMessage = (message: string, conversationId: string | null) =>
  request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

export const listConversations = () => request<Conversation[]>("/conversations");

export const getConversation = async (id: string): Promise<Message[]> => {
  const rows = await request<Array<Omit<Message, "id"> & { id: number }>>(`/conversations/${id}`);
  return rows.map((r) => ({ ...r, id: String(r.id), sources: r.sources ?? [] }));
};

export const deleteConversation = (id: string) =>
  request<{ ok: boolean }>(`/conversations/${id}`, { method: "DELETE" });
