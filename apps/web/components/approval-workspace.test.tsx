import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApprovalWorkspace } from "./approval-workspace";

const pendingApproval = {
  approval_id: "APR-TEST184",
  action: "assign_technician",
  ticket_id: "184",
  ticket_title: "Compressor pressure loss",
  from_technician_id: null,
  from_technician_name: null,
  to_technician_id: "T-001",
  to_technician_name: "James Chen",
  reason: "Highest ranked eligible technician for the compressor incident.",
  status: "pending",
  requested_by: "agent:run-test",
  requested_at: "2026-10-07T16:00:00Z",
  expires_at: "2026-10-07T16:30:00Z",
  decided_by: null,
  decided_at: null,
  decision_comment: null,
  evidence: {
    policy_version: "dispatch-v2-routes",
    score: 74.2,
    distance_km: 78.1,
    travel_duration_minutes: 97.6,
    route_provider: "mock",
    route_is_estimate: true,
    matched_certification_ids: ["CERT-HVAC-2"],
  },
  version: 1,
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ApprovalWorkspace", () => {
  it("renders evidence and records an explicit approval decision", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [pendingApproval], total: 1 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          ...pendingApproval,
          status: "approved",
          decided_by: "supervisor@example.test",
          decided_at: "2026-10-07T16:05:00Z",
          decision_comment: "Coverage reviewed.",
          version: 2,
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<ApprovalWorkspace />);

    expect(
      await screen.findByText("Compressor pressure loss"),
    ).toBeInTheDocument();
    expect(screen.getByText("James Chen")).toBeInTheDocument();
    expect(screen.getByText("74.20")).toBeInTheDocument();
    expect(screen.getByText("Estimate")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reviewer identity"), {
      target: { value: "supervisor@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Decision comment"), {
      target: { value: "Coverage reviewed." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(
      await screen.findByText("Authorized only · execution awaits Phase 8"),
    ).toBeInTheDocument();
    const decisionCall = fetchMock.mock.calls[1];
    expect(decisionCall[0]).toContain("/api/approvals/APR-TEST184/approve");
    expect(JSON.parse(String(decisionCall[1]?.body))).toEqual({
      decided_by: "supervisor@example.test",
      comment: "Coverage reviewed.",
    });
  });

  it("filters terminal approvals and never shows decision actions for them", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            {
              ...pendingApproval,
              approval_id: "APR-EXPIRED",
              status: "expired",
            },
          ],
          total: 1,
        }),
      }),
    );
    render(<ApprovalWorkspace />);

    await screen.findByText("Compressor pressure loss");
    expect(
      screen.queryByRole("button", { name: "Approve" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("This proposal cannot be executed"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pending" }));
    expect(
      screen.getByText("No pending approval requests."),
    ).toBeInTheDocument();
  });

  it("announces queue and decision failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );
    render(<ApprovalWorkspace />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Approval queue unavailable",
      ),
    );
  });
});
