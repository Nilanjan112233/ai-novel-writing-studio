"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BookOpen } from 'lucide-react'
import ThemeToggle from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'

const links = [
  { href: '/projects', label: 'Projects' },
  { href: '/settings', label: 'AI settings' },
]

/** Top bar for the pages outside a project: home, projects and AI settings. */
export default function AppHeader() {
  const pathname = usePathname() || '/'
  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur" data-testid="app-header">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-4 sm:px-8">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground"><BookOpen className="h-4 w-4" /></span>
          NovelForge
        </Link>
        <nav className="flex items-center gap-1 text-sm" aria-label="Main">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn('rounded-md px-3 py-1.5 transition-colors', pathname.startsWith(link.href) ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:text-foreground')}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <ThemeToggle className="ml-auto" />
      </div>
    </header>
  )
}
