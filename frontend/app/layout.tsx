import type { Metadata } from "next"
import "./globals.css"
import { themeBootScript } from "@/lib/theme"

export const metadata: Metadata = {
  title: "NovelForge",
  description: "Plan, write and finish a novel with an AI writing partner that remembers your story.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
      </head>
      <body className="font-sans">{children}</body>
    </html>
  )
}
