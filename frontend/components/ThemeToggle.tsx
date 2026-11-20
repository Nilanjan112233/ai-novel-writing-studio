"use client"

import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { cn } from '@/lib/utils'
import { THEME_STORAGE_KEY as STORAGE_KEY } from '@/lib/theme'

export function readStoredTheme(): 'light' | 'dark' | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

export default function ThemeToggle({ className, showLabel = false }: { className?: string; showLabel?: boolean }) {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    setDark(document.documentElement.classList.contains('dark'))
  }, [])
  const toggle = () => {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle('dark', next)
    try { window.localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light') } catch { /* theme still applies for this visit */ }
  }
  const label = dark ? 'Switch to light mode' : 'Switch to dark mode'
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      data-testid="theme-toggle"
      className={cn('inline-flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground', className)}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      {showLabel ? <span>{dark ? 'Light mode' : 'Dark mode'}</span> : null}
    </button>
  )
}
