import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import TechniciansPage from "./technicians/page";
import TicketsPage from "./tickets/page";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("catalog pages", () => {
  it("renders ticket records returned by the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          total: 1,
          limit: 100,
          offset: 0,
          items: [
            {
              ticket_id: "184",
              title: "Compressor pressure loss",
              priority: "critical",
              status: "open",
              customer_name: "Northstar Grocers",
              site_name: "San Francisco Market",
              city: "San Francisco",
              state: "CA",
              equipment_type: "compressor",
              required_certification_ids: ["CERT-REFRIG"],
              resolution_due_at: "2026-10-06T18:00:00Z",
              sla_state: "at_risk",
              assigned_technician_name: null,
            },
          ],
        }),
      }),
    );

    render(<TicketsPage />);

    expect(
      await screen.findByText("Compressor pressure loss"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /#184/i })).toHaveAttribute(
      "href",
      "/tickets/184",
    );
    expect(screen.getByText("Northstar Grocers")).toBeInTheDocument();
  });

  it("renders technician qualifications returned by the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          total: 1,
          limit: 100,
          offset: 0,
          items: [
            {
              technician_id: "T-001",
              name: "James Chen",
              email: "james.chen@geoops.example",
              phone: "+1-415-555-1001",
              status: "available",
              home_city: "San Francisco",
              current_location: { latitude: 37.781, longitude: -122.411 },
              skill_tags: ["hvac", "controls"],
              completed_jobs: 184,
              average_rating: 4.8,
              certifications: [],
              active_assignment_count: 0,
            },
          ],
        }),
      }),
    );

    render(<TechniciansPage />);

    expect(await screen.findByText("James Chen")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /James Chen/i })).toHaveAttribute(
      "href",
      "/technicians/T-001",
    );
    expect(screen.getByText("184")).toBeInTheDocument();
  });
});
