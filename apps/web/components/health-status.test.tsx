import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HealthStatus } from "./health-status";

const healthyPayload = {
  status: "ok",
  service: "geoops-api",
  environment: "development",
  version: "0.1.0",
} as const;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("HealthStatus", () => {
  it("shows a loading state while the request is pending", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => undefined)),
    );

    render(<HealthStatus />);

    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    expect(screen.getByRole("button", { name: "Recheck" })).toBeDisabled();
  });

  it("renders live service metadata after a successful check", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => healthyPayload,
      }),
    );

    render(<HealthStatus />);

    expect(await screen.findByText("Operational")).toBeInTheDocument();
    expect(screen.getByText("geoops-api")).toBeInTheDocument();
    expect(screen.getByText("development")).toBeInTheDocument();
    expect(screen.getByText("v0.1.0")).toBeInTheDocument();
  });

  it("shows a useful error when the API cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network unavailable")),
    );

    render(<HealthStatus />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Network unavailable",
    );
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("retries a failed check", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("First request failed"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => healthyPayload,
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthStatus />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Recheck" }));

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Operational"),
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
