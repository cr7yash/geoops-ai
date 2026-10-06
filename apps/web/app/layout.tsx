import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
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
      <body>{children}</body>
    </html>
  );
}
