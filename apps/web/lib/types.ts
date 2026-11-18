export type TicketPriority = "low" | "medium" | "high" | "critical";
export type TicketStatus =
  "open" | "assigned" | "in_progress" | "on_hold" | "completed" | "cancelled";
export type TechnicianStatus =
  "available" | "dispatched" | "off_duty" | "unavailable";

export type GeoPoint = { latitude: number; longitude: number };

export type TicketSummary = {
  ticket_id: string;
  title: string;
  priority: TicketPriority;
  status: TicketStatus;
  customer_name: string;
  site_name: string;
  city: string;
  state: string;
  equipment_type: string;
  required_certification_ids: string[];
  resolution_due_at: string;
  sla_state: "overdue" | "at_risk" | "on_track" | "met";
  assigned_technician_name: string | null;
};

export type Assignment = {
  assignment_id: string;
  ticket_id: string;
  technician_id: string;
  technician_name: string;
  ticket_title?: string | null;
  scheduled_start: string;
  scheduled_end: string;
  status: "scheduled" | "active" | "completed" | "cancelled";
  created_at: string;
};

export type TicketDetail = {
  ticket_id: string;
  customer_id: string;
  customer_name: string;
  site_id: string;
  site: {
    site_id: string;
    customer_id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    postal_code: string;
    timezone: string;
    location: GeoPoint | null;
    geocode_status: string;
    routing_mode: string;
  };
  title: string;
  description: string;
  equipment_type: string;
  equipment_id: string;
  required_certification_ids: string[];
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
  response_due_at: string;
  resolution_due_at: string;
  sla_state: "overdue" | "at_risk" | "on_track" | "met";
  assignments: Assignment[];
};

export type Certification = {
  certification_id: string;
  name: string;
  expires_on: string;
  validity: "valid" | "expiring_soon" | "expired";
};

export type TechnicianSummary = {
  technician_id: string;
  name: string;
  email: string;
  phone: string;
  status: TechnicianStatus;
  home_city: string;
  current_location: GeoPoint;
  skill_tags: string[];
  completed_jobs: number;
  average_rating: number;
  certifications: Certification[];
  active_assignment_count: number;
};

export type TechnicianDetail = Omit<
  TechnicianSummary,
  "active_assignment_count"
> & {
  assignments: Assignment[];
};

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type DispatchExclusionReason =
  | "unavailable"
  | "missing_required_certification"
  | "expired_required_certification"
  | "schedule_conflict"
  | "site_location_unavailable"
  | "outside_service_radius"
  | "route_unavailable"
  | "exceeds_maximum_travel_time";

export type DispatchScoreBreakdown = {
  certification: number;
  travel_time: number;
  workload: number;
  performance: number;
  experience: number;
};

export type DispatchCandidate = {
  rank: number | null;
  technician_id: string;
  technician_name: string;
  status: TechnicianStatus;
  eligible: boolean;
  exclusion_reasons: DispatchExclusionReason[];
  straight_line_distance_km: number | null;
  distance_km: number | null;
  travel_duration_minutes: number | null;
  route_provider: string | null;
  route_is_estimate: boolean | null;
  active_assignment_count: number;
  matched_certification_ids: string[];
  score: number | null;
  score_breakdown: DispatchScoreBreakdown | null;
};

export type DispatchRecommendation = {
  ticket_id: string;
  ticket_title: string;
  priority: TicketPriority;
  sla_state: "overdue" | "at_risk" | "on_track" | "met";
  policy_version: string;
  evaluated_at: string;
  service_window_start: string;
  service_window_end: string;
  maximum_distance_km: number;
  maximum_travel_minutes: number;
  maps_provider: string;
  required_certification_ids: string[];
  recommended_technician_id: string | null;
  eligible_candidates: DispatchCandidate[];
  excluded_candidates: DispatchCandidate[];
  total_evaluated: number;
};

export type KnowledgeDocumentType =
  "contract" | "manual" | "service_report" | "incident_history" | "policy";

export type KnowledgeDocumentSummary = {
  document_id: string;
  title: string;
  document_type: KnowledgeDocumentType;
  version: string;
  effective_date: string | null;
  customer_id: string | null;
  equipment_type: string | null;
  storage_uri: string;
};

export type KnowledgeDocumentList = {
  items: KnowledgeDocumentSummary[];
  total: number;
};

export type KnowledgeSource = {
  rank: number;
  score: number;
  citation: string;
  chunk_id: string;
  document_id: string;
  title: string;
  document_type: KnowledgeDocumentType;
  version: string;
  effective_date: string | null;
  customer_id: string | null;
  equipment_type: string | null;
  section: string;
  excerpt: string;
  storage_uri: string;
};

export type KnowledgeSearchRequest = {
  query: string;
  customer_id?: string;
  equipment_type?: string;
  document_type?: KnowledgeDocumentType;
  limit?: number;
};

export type KnowledgeSearchResponse = {
  query: string;
  result_count: number;
  sources: KnowledgeSource[];
};

export type AgentToolUse = {
  tool: string;
  status: "success" | "error";
  latency_ms: number;
  summary: string;
  retrieval_count: number | null;
};

export type AgentRecommendedAction = {
  kind: "review_dispatch_recommendation" | "review_approval_request";
  label: string;
  ticket_id: string;
  technician_id: string | null;
  approval_id: string | null;
};

export type ApprovalStatus =
  "pending" | "approved" | "rejected" | "expired" | "executed" | "failed";

export type ApprovalRequest = {
  approval_id: string;
  action: "assign_technician";
  ticket_id: string;
  ticket_title: string;
  from_technician_id: string | null;
  from_technician_name: string | null;
  to_technician_id: string;
  to_technician_name: string;
  reason: string;
  status: ApprovalStatus;
  requested_by: string;
  requested_at: string;
  expires_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_comment: string | null;
  evidence: {
    policy_version: string;
    score: number;
    distance_km: number | null;
    travel_duration_minutes: number | null;
    route_provider: string | null;
    route_is_estimate: boolean | null;
    matched_certification_ids: string[];
  };
  version: number;
};

export type ApprovalListResponse = {
  items: ApprovalRequest[];
  total: number;
};

export type ApprovalDecisionRequest = {
  decided_by: string;
  comment?: string;
};

export type AgentChatRequest = {
  message: string;
  session_id?: string;
};

export type AgentChatResponse = {
  answer: string;
  recommended_action: AgentRecommendedAction | null;
  sources: KnowledgeSource[];
  tools_used: AgentToolUse[];
  confidence: number;
  requires_approval: boolean;
  trace_id: string;
  session_id: string;
  agent_run_id: string;
  model_provider: string;
  model_name: string;
};
