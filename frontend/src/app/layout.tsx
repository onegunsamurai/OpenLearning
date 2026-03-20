import type { Metadata } from "next";
import { Syne, IBM_Plex_Mono, DM_Sans } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const syne = Syne({
  variable: "--font-heading",
  subsets: ["latin"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "OpenLearning — AI-Powered Learning Engineer",
  description:
    "Identify skill gaps and generate personalized learning plans powered by AI.",
  metadataBase: new URL("https://openlearning.dev"),
  openGraph: {
    title: "OpenLearning — AI-Powered Learning Engineer",
    description:
      "Identify skill gaps and generate personalized learning plans powered by AI.",
    url: "https://openlearning.dev",
    siteName: "OpenLearning",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "OpenLearning — AI-Powered Learning Engineer",
    description:
      "Identify skill gaps and generate personalized learning plans powered by AI.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${syne.variable} ${ibmPlexMono.variable} ${dmSans.variable} antialiased`}
      >
        <TooltipProvider>
          <AuthProvider>{children}</AuthProvider>
        </TooltipProvider>
        <Analytics />
      </body>
    </html>
  );
}
