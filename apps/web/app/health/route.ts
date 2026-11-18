import type { NextRequest } from "next/server";

import { GET as proxy } from "../api/[...path]/route";

export async function GET(request: NextRequest) {
  return proxy(request, { params: Promise.resolve({ path: ["health"] }) });
}
