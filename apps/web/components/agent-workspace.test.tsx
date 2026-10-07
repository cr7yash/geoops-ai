import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentWorkspace } from "./agent-workspace";

const response = {
  answer:
    "James Chen is the highest-ranked eligible technician for ticket 184. No assignment was changed.",
  recommended_action: {
    kind: "review_dispatch_recommendation",
    label: "Review James Chen for ticket 184",
    ticket_id: "184",
    technician_id: "T-001",
  },
  sources: [],
  tools_used: [
    {
      tool: "get_ticket",
      status: "success",
      latency_ms: 1.25,
      summary: "Loaded ticket 184.",
      retrieval_count: null,
    },
    {
      tool: "recommend_assignment",
      status: "success",
      latency_ms: 2.5,
      summary: "Recommended James Chen for ticket 184.",
      retrieval_count: 2,
    },
  ],
  confidence: 0.99,
  requires_approval: false,
  trace_id: "trace-agent-test-184",
  session_id: "session-agent-test-184",
  agent_run_id: "run-agent-test-184",
  model_provider: "local",
  model_name: "geoops-local-planner-v1",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AgentWorkspace", () => {
  it("renders an answer and safe tool evidence", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => response,
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AgentWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Ask GeoOps" }));

    expect(await screen.findByText(/James Chen is the highest-ranked/)).toBeInTheDocument();
    expect(screen.getByText("Get Ticket")).toBeInTheDocument();
    expect(screen.getByText("Recommend Assignment")).toBeInTheDocument();
    expect(screen.getByText("Review James Chen for ticket 184")).toBeInTheDocument();
    expect(screen.getByText("99% confidence")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/chat",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows the approval boundary without implying execution", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ...response,
          answer: "I cannot change an assignment in Phase 6.",
          recommended_action: null,
          tools_used: [],
          requires_approval: true,
        }),
      }),
    );
    render(<AgentWorkspace />);
    fireEvent.change(screen.getByLabelText("Operational question"), {
      target: { value: "Reassign ticket 184 to James Chen" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask GeoOps" }));

    expect(await screen.findByText("Approval required")).toBeInTheDocument();
    expect(screen.getByText("No operational tool was run.")).toBeInTheDocument();
    expect(screen.queryByText("Recommended next review")).not.toBeInTheDocument();
  });

  it("announces API failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );
    render(<AgentWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Ask GeoOps" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Agent unavailable"),
    );
  });
});
