import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "小苏 · 企业 AI 助手",
  description: "公司内部知识库智能问答与管理后台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
