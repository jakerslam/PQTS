import type { Metadata } from "next";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "PQTS Web",
  description: "PQTS control dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
