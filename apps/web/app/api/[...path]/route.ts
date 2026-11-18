import { NextRequest } from "next/server";

const allowed = new Set([
  "chat",
  "tickets",
  "technicians",
  "dispatch",
  "maps",
  "knowledge",
  "approvals",
  "evaluations",
  "operations",
  "assignments",
  "health",
]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (!path[0] || !allowed.has(path[0]))
    return new Response("Not found", { status: 404 });
  const origin = process.env.API_INTERNAL_BASE_URL ?? "http://127.0.0.1:8000";
  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });
  if (process.env.GEOOPS_API_TOKEN)
    headers.set("X-Geoops-Token", process.env.GEOOPS_API_TOKEN);
  if (process.env.API_USE_GOOGLE_ID_TOKEN === "true") {
    const token = await fetch(
      `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(origin)}`,
      { headers: { "Metadata-Flavor": "Google" }, cache: "no-store" },
    );
    if (!token.ok)
      return Response.json(
        { detail: "Service identity unavailable" },
        { status: 503 },
      );
    headers.set("Authorization", `Bearer ${await token.text()}`);
  }
  try {
    const apiPath =
      path.length === 1 && path[0] === "health"
        ? "/health"
        : `/api/${path.map(encodeURIComponent).join("/")}`;
    const response = await fetch(
      `${origin}${apiPath}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        cache: "no-store",
        body: request.method === "GET" ? undefined : await request.text(),
        signal: AbortSignal.timeout(180_000),
      },
    );
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "X-Request-ID": response.headers.get("x-request-id") ?? "",
      },
    });
  } catch {
    return Response.json({ detail: "API unavailable" }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
