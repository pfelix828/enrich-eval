import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EnrichEval — a quality lab for transaction enrichment",
  description:
    "Portfolio demo: an evaluation harness that measures transaction-enrichment quality and turns vague customer complaints into ranked, fixable root causes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Nav />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-border-subtle bg-white">
          <div className="mx-auto max-w-6xl space-y-2 px-4 py-6 text-xs text-muted">
            <p>
              Independent portfolio project by Philip Felix. The category taxonomy comes from Plaid&apos;s public
              Personal Finance Category documentation; no Plaid systems or data are involved.
            </p>
            <p>
              Every number shown is computed from a 55-row synthetic seed of transaction descriptors scored by a
              deterministic rules enricher. The harness is the point: the same metrics, investigation, and regression
              layers work unchanged against a production enricher.{" "}
              <a href="https://github.com/pfelix828/enrich-eval" className="underline decoration-dotted underline-offset-2 hover:text-foreground">
                Code on GitHub
              </a>
              .
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
