import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

// One typeface everywhere; cyrillic-ext covers Kazakh letters (ә ғ қ ң ө ұ ү һ і).
const inter = Inter({ variable: "--font-inter", subsets: ["latin", "cyrillic", "cyrillic-ext"] });

export const metadata: Metadata = {
  title: { default: "Qoldau — SDU University student support", template: "%s · Qoldau" },
  description:
    "Ask once in Kazakh, Russian or English — Qoldau understands your request and routes it to the right SDU University office, then tracks it to resolution.",
  openGraph: {
    title: "Qoldau — SDU University student support",
    description: "One place for every student request at SDU University. AI routing, live tracking, real answers.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
