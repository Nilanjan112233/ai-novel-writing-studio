import fs from 'fs'
import type { APIRequestContext } from '@playwright/test'

/** Backend URL used by the dev launcher (honours a moved backend port). */
export function backendUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'))
    return `http://127.0.0.1:${ports.backendPort || 8000}`
  }
  return 'http://127.0.0.1:8000'
}

/**
 * True when at least one real AI provider has a key saved in NovelForge's
 * settings. Specs that need real prose skip themselves otherwise, because the
 * offline mock provider cannot write schema-valid scene text.
 */
export async function realAiConfigured(request: APIRequestContext, apiBase: string): Promise<boolean> {
  const response = await request.get(`${apiBase}/api/settings/ai`).catch(() => null)
  if (!response || !response.ok()) return false
  const body = await response.json()
  return Object.entries(body.providers || {}).some(([name, provider]) => name !== 'mock' && Boolean((provider as { configured?: boolean })?.configured))
}

export const NEEDS_REAL_AI = 'Needs a real AI provider (the offline mock cannot write schema-valid scene prose)'
