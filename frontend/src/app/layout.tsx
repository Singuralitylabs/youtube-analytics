import type { Metadata } from "next";

import { Sidebar } from "@/components/layout/Sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "YouTube Analytics",
  description: "自チャンネルのパフォーマンス可視化ダッシュボード",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-x-hidden">
            <div className="mx-auto w-full max-w-7xl px-6 py-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
