import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "vietnamese"],
});

export const metadata: Metadata = {
  title: "RAQ Chatbot — Trợ lý Thư viện Tri thức",
  description:
    "Nền tảng quản lý kho tri thức tích hợp Chatbot AI hỏi đáp RAG và sinh đề trắc nghiệm tự động",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[var(--bg-primary)]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
