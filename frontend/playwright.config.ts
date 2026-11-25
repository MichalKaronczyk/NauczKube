import { defineConfig, devices } from '@playwright/test'

/** Testy E2E: pełna sesja K01 od startu do podsumowania.
 *  Wymagają działającego backendu (`uvicorn app.main:app`) z zbudowanym frontendem. */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'ipad', use: { ...devices['iPad Pro 11 landscape'] } },
  ],
})
