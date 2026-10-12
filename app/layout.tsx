import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Radius Team Entry",
  description: "Discord大会のチーム登録・承認・ランクポイントを管理。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="antialiased">{children}</body>
    </html>
  );
}
