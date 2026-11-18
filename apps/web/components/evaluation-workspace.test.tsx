import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { EvaluationWorkspace } from "./evaluation-workspace";

afterEach(() => vi.unstubAllGlobals());

it("starts empty, then displays the actual saved run and missing measurements", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [] })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          run_id: "eval-test",
          created_at: "2026-11-17T12:00:00Z",
          provider: "local",
          model: "planner",
          dataset_sha256: "dataset",
          passed: true,
          thresholds: {},
          metrics: { task_success: 0.75 },
          results: [
            {
              case_id: "approval",
              task_success: true,
              tool_selection_accuracy: 1,
              policy_compliance: 1,
              latency_ms: 3,
              error_type: null,
            },
          ],
        }),
      }),
  );
  render(<EvaluationWorkspace />);
  expect(await screen.findByText(/No evaluation runs yet/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Run evaluation" }));
  expect(await screen.findByText("75.0%")).toBeInTheDocument();
  expect(screen.getByText("Regression gate passed")).toBeInTheDocument();
  expect(screen.getAllByText("Not reported").length).toBeGreaterThan(0);
});
