import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RN Classes Video Studio",
  description: "Get a step-by-step video solution for maths and science problems.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
