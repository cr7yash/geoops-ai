import type { Metadata, Viewport } from "next";
import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeoOps AI | Operations Console",
  description: "Geospatial AI operations for field-service teams.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#07110f",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Suspense
          fallback={<div className="shell-loading">Loading GeoOps…</div>}
        >
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
