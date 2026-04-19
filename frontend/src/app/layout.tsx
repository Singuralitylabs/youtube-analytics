import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-manrope",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Studio Console — YouTube Analytics",
  description: "自チャンネルのパフォーマンスを編集者の視点で可視化",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className={`${manrope.variable} ${plexMono.variable}`}>
      <body className="min-h-screen">
        <div className="flex min-h-screen">
          <Sidebar />
          <div
            className="flex min-h-screen flex-1 flex-col"
            style={{ marginLeft: "var(--sidebar-w)" }}
          >
            <TopBar />
            <main className="flex-1">
              <div className="mx-auto w-full max-w-[1440px] px-8 py-8">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
