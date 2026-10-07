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
