import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import QueryClientProvider from "../components/QueryClientProvider";
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
  title: "App Review Insights",
  description: "Analyze app reviews and gain insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-gray-50">
        <QueryClientProvider>{children}</QueryClientProvider>
      </body>
    </html>
  );
}