import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "NovelForge - Narrative Intelligence",
  description: "A local, author-controlled narrative intelligence studio for long-form fiction",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  )
}
