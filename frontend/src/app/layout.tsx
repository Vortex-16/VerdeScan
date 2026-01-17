import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VerdeScan | AI-Powered Afforestation Monitoring",
  description: "Monitor sapling survival across forest patches using AI-analyzed drone imagery. Track every tree, protect every forest.",
  keywords: "afforestation, forest monitoring, AI, drone imagery, sapling survival, VerdeScan, Odisha Forest Department",
  authors: [{ name: "VerdeScan Team" }],
  openGraph: {
    title: "VerdeScan | AI-Powered Afforestation Monitoring",
    description: "Monitor sapling survival across forest patches using AI-analyzed drone imagery.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
