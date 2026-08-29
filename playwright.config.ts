import { defineConfig, devices } from '@playwright/test'

const e2eDatabase = process.env.NOVELFORGE_E2E_DATABASE || 'novelforge_e2e'
if (!e2eDatabase.toLowerCase().includes('e2e')) {
  throw new Error('Playwright requires a dedicated database name containing "e2e".')
}
process.env.NOVELFORGE_E2E_DATABASE = e2eDatabase
process.env.DATABASE_NAME = e2eDatabase

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: false,
    timeout: 120000,
    env: {
      ...process.env,
      DATABASE_NAME: e2eDatabase,
      NOVELFORGE_E2E_DATABASE: e2eDatabase,
    },
  },
})
