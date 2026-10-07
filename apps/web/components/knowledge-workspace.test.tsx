import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeWorkspace } from "./knowledge-workspace";

const documents = {
  total: 1,
  items: [
    {
      document_id: "KB-MANUAL-COMP-001",
      title: "Compressor Field Service Manual",
      document_type: "manual",
      version: "2.1",
      effective_date: "2026-01-15",
      customer_id: null,
      equipment_type: "compressor",
      storage_uri: "manuals/compressor-field-service.md",
    },
  ],
};

const result = {
  query: "What should be checked first for compressor pressure loss?",
  result_count: 1,
  sources: [
    {
      rank: 1,
      score: 0.8123,
      citation:
        "[Compressor Field Service Manual v2.1 — Initial diagnostic sequence]",
      chunk_id: "KB-MANUAL-COMP-001:abc",
      document_id: "KB-MANUAL-COMP-001",
      title: "Compressor Field Service Manual",
      document_type: "manual",
      version: "2.1",
      effective_date: "2026-01-15",
      customer_id: null,
      equipment_type: "compressor",
      section: "Initial diagnostic sequence",
      excerpt:
        "First compare suction and discharge pressure with the controller trend and a calibrated manifold.",
      storage_uri: "manuals/compressor-field-service.md",
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("KnowledgeWorkspace", () => {
  it("renders indexed documents and cited retrieval results", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((_input: RequestInfo | URL, init?: RequestInit) =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (init?.method === "POST" ? result : documents),
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<KnowledgeWorkspace />);

    expect(
      await screen.findByText("Compressor Field Service Manual"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Document type"), {
      target: { value: "manual" },
    });
    fireEvent.change(screen.getByLabelText("Equipment type"), {
      target: { value: "compressor" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search sources" }));

    expect(
      await screen.findByText("Initial diagnostic sequence"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "[Compressor Field Service Manual v2.1 — Initial diagnostic sequence]",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("81.2%")).toBeInTheDocument();

    const searchCall = fetchMock.mock.calls.find(
      ([, init]) => (init as RequestInit | undefined)?.method === "POST",
    );
    expect(JSON.parse(String(searchCall?.[1]?.body))).toMatchObject({
      document_type: "manual",
      equipment_type: "compressor",
      limit: 6,
    });
  });

  it("shows an explicit empty state without inventing an answer", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation((_input: RequestInfo | URL, init?: RequestInit) =>
          Promise.resolve({
            ok: true,
            status: 200,
            json: async () =>
              init?.method === "POST"
                ? { query: "unknown", result_count: 0, sources: [] }
                : documents,
          }),
        ),
    );

    render(<KnowledgeWorkspace />);
    await screen.findByText("Source catalog");
    fireEvent.click(screen.getByRole("button", { name: "Search sources" }));

    expect(
      await screen.findByText(
        "No source passages matched the query and filters.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /answer/i }),
    ).not.toBeInTheDocument();
  });

  it("announces a retrieval failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation((_input: RequestInfo | URL, init?: RequestInit) =>
          init?.method === "POST"
            ? Promise.resolve({ ok: false, status: 503 })
            : Promise.resolve({
                ok: true,
                status: 200,
                json: async () => documents,
              }),
        ),
    );

    render(<KnowledgeWorkspace />);
    await screen.findByText("Source catalog");
    fireEvent.click(screen.getByRole("button", { name: "Search sources" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Knowledge search unavailable",
      ),
    );
  });
});
