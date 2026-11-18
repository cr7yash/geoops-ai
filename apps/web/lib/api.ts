import type {
  AgentChatRequest,
  AgentChatResponse,
  ApprovalDecisionRequest,
  ApprovalListResponse,
  ApprovalRequest,
  DispatchRecommendation,
  KnowledgeDocumentList,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
  Paginated,
  TechnicianDetail,
  TechnicianSummary,
  TicketDetail,
  TicketSummary,
} from "@/lib/types";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    if (response.status === 404) throw new Error("not_found");
    throw new Error(`API request failed with HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(body),
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    method: "POST",
    signal,
  });
  if (!response.ok) {
    throw new Error(`API request failed with HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getTickets(query: URLSearchParams, signal?: AbortSignal) {
  return getJson<Paginated<TicketSummary>>(
    `/api/tickets?${query.toString()}`,
    signal,
  );
}

export function getTicket(ticketId: string, signal?: AbortSignal) {
  return getJson<TicketDetail>(
    `/api/tickets/${encodeURIComponent(ticketId)}`,
    signal,
  );
}

export function getTechnicians(query: URLSearchParams, signal?: AbortSignal) {
  return getJson<Paginated<TechnicianSummary>>(
    `/api/technicians?${query.toString()}`,
    signal,
  );
}

export function getTechnician(technicianId: string, signal?: AbortSignal) {
  return getJson<TechnicianDetail>(
    `/api/technicians/${encodeURIComponent(technicianId)}`,
    signal,
  );
}

export function getDispatchRecommendation(
  ticketId: string,
  signal?: AbortSignal,
) {
  return getJson<DispatchRecommendation>(
    `/api/dispatch/recommendations/${encodeURIComponent(ticketId)}`,
    signal,
  );
}

export function getKnowledgeDocuments(signal?: AbortSignal) {
  return getJson<KnowledgeDocumentList>("/api/knowledge/documents", signal);
}

export function searchKnowledge(
  request: KnowledgeSearchRequest,
  signal?: AbortSignal,
) {
  return postJson<KnowledgeSearchResponse>(
    "/api/knowledge/search",
    request,
    signal,
  );
}

export function askAgent(request: AgentChatRequest, signal?: AbortSignal) {
  return postJson<AgentChatResponse>("/api/chat", request, signal);
}

export function getApprovals(signal?: AbortSignal) {
  return getJson<ApprovalListResponse>("/api/approvals", signal);
}

export function decideApproval(
  approvalId: string,
  decision: "approve" | "reject",
  request: ApprovalDecisionRequest,
  signal?: AbortSignal,
) {
  return postJson<ApprovalRequest>(
    `/api/approvals/${encodeURIComponent(approvalId)}/${decision}`,
    request,
    signal,
  );
}

export function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}
