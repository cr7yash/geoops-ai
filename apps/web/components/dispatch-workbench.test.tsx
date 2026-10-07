import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DispatchWorkbench } from "./dispatch-workbench";

const ticket = {
  ticket_id: "184",
  title: "Compressor pressure loss",
  priority: "critical",
  status: "open",
  customer_name: "Harbor Hospitality",
  site_name: "Napa Resort",
  city: "Napa",
  state: "CA",
  equipment_type: "compressor",
  required_certification_ids: ["CERT-REFRIG"],
  resolution_due_at: "2026-10-06T18:00:00Z",
  sla_state: "at_risk",
  assigned_technician_name: null,
};

const recommendation = {
  ticket_id: "184",
  ticket_title: "Compressor pressure loss",
  priority: "critical",
  sla_state: "at_risk",
  policy_version: "dispatch-v1",
  evaluated_at: "2026-10-06T12:00:00Z",
  service_window_start: "2026-10-06T13:00:00Z",
  service_window_end: "2026-10-06T17:00:00Z",
  maximum_distance_km: 65,
  required_certification_ids: ["CERT-REFRIG"],
  recommended_technician_id: "T-001",
  total_evaluated: 15,
  eligible_candidates: [
    {
      rank: 1,
      technician_id: "T-001",
      technician_name: "James Chen",
      status: "available",
      eligible: true,
      exclusion_reasons: [],
      distance_km: 64,
      active_assignment_count: 0,
      matched_certification_ids: ["CERT-REFRIG"],
      score: 62.39,
      score_breakdown: {
        certification: 25,
        proximity: 0.46,
        workload: 20,
        performance: 14.4,
        experience: 9.2,
      },
    },
  ],
  excluded_candidates: [
    {
      rank: null,
      technician_id: "T-015",
      technician_name: "Riley Morgan",
      status: "unavailable",
      eligible: false,
      exclusion_reasons: ["unavailable", "missing_required_certification"],
      distance_km: 41.2,
      active_assignment_count: 0,
      matched_certification_ids: [],
      score: null,
      score_breakdown: null,
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("DispatchWorkbench", () => {
  it("renders the recommended candidate and score evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        const payload = url.includes("/api/tickets?")
          ? { total: 1, limit: 100, offset: 0, items: [ticket] }
          : recommendation;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => payload,
        });
      }),
    );

    render(<DispatchWorkbench initialTicketId="184" />);

    expect(
      await screen.findByText("Recommended technician"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("James Chen")).toHaveLength(2);
    expect(screen.getAllByText("62.4")).toHaveLength(2);
    expect(screen.getByText("dispatch-v1")).toBeInTheDocument();
    expect(
      screen.getByText("Why 1 technicians were excluded"),
    ).toBeInTheDocument();
  });

  it("shows an honest manual-review state when nobody is eligible", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);
        const payload = url.includes("/api/tickets?")
          ? { total: 1, limit: 100, offset: 0, items: [ticket] }
          : {
              ...recommendation,
              recommended_technician_id: null,
              eligible_candidates: [],
              excluded_candidates: recommendation.excluded_candidates,
            };
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => payload,
        });
      }),
    );

    render(<DispatchWorkbench initialTicketId="184" />);

    expect(
      await screen.findByText("No technician passed every eligibility gate."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Recommended technician"),
    ).not.toBeInTheDocument();
  });
});
