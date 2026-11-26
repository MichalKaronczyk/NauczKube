/**
 * Zrzuty ekranu do dokumentacji (docs/zrzuty/instrukcja/*.png), 1440×900.
 *
 *   BASE_URL=http://127.0.0.1:8077 npx playwright test e2e/zrzuty.spec.ts --project=chromium
 *
 * Każdy zrzut to prawdziwy stan aplikacji, nie makieta: test przechodzi
 * pełną sesję K01 dokładnie tak, jak robi to uczeń.
 */

import { expect, test, type Page } from '@playwright/test'

const DIR = '../docs/zrzuty/instrukcja'

test.use({ viewport: { width: 1440, height: 900 } })

const shot = async (page: Page, name: string) => {
  await page.waitForTimeout(500)
  await page.screenshot({ path: `${DIR}/${name}.png` })
}

test('zrzuty: pełna sesja ucznia', async ({ page }) => {
  test.setTimeout(240_000)

  // 1. Start
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Naucz Kubę' })).toBeVisible()
  await shot(page, '1-start')

  await page.getByRole('button', { name: 'Ćwiczę sam' }).click()
  await page.getByLabel(/pseudonim/i).fill('Ola')
  await page.getByRole('button', { name: 'Zaczynamy' }).click()

  // 2. Tematy
  await expect(page.getByRole('heading', { name: 'Tematy' })).toBeVisible()
  await shot(page, '2-tematy')

  await page.locator('.topic-row', { hasText: 'Kwadrat sumy' }).click()
  await expect(page.locator('.board-paper')).toBeVisible()

  // 3. Karta „Jak to działa” przy pierwszym wejściu
  const tutorial = page.getByRole('button', { name: 'Rozumiem, zaczynamy' })
  if (await tutorial.isVisible().catch(() => false)) {
    await shot(page, '3-jak-to-dziala')
    await tutorial.click()
  }
  await expect(page.locator('.tutorial')).toHaveCount(0)

  // 4. Tablica — Kuba napisał całe rozwiązanie
  const lines = page.locator('.kuba-line')
  await expect(lines).toHaveCount(4)
  await expect(lines.nth(3)).toHaveClass(/is-shown/, { timeout: 20_000 })
  await expect(page.locator('.bubble-kuba').first()).toBeVisible()
  await shot(page, '4-tablica')

  // 5. Zakreślenie błędnej linijki (druga) → Kuba się broni
  await lines.nth(1).click()
  await expect(page.getByLabel('Twoje wyjaśnienie')).toBeVisible({ timeout: 20_000 })
  await shot(page, '5-zakreslenie')

  // 6. Rozmowa — wyjaśnienie ucznia i ocena kluczowych idei
  const textarea = page.getByLabel('Twoje wyjaśnienie')
  await textarea.fill('Brakuje wyrazu 2ab.')
  await page.getByRole('button', { name: 'Wyślij' }).click()
  await expect(page.locator('.ideas li.is-covered')).toHaveCount(1, { timeout: 30_000 })
  await shot(page, '6-rozmowa')

  await textarea.fill('Podstaw x = 1 i porównaj obie strony, wyjdzie inaczej.')
  await page.getByRole('button', { name: 'Wyślij' }).click()
  await expect(page.locator('.ideas li.is-covered')).toHaveCount(2, { timeout: 30_000 })

  // 7. Zadanie transferowe
  const transfer = page.getByRole('button', { name: 'Dobrze zrobione' })
  await expect(transfer).toBeVisible({ timeout: 30_000 })
  await shot(page, '7-transfer')
  await transfer.click()

  // 8. Podsumowanie
  await expect(page.getByRole('heading', { name: /Wytłumaczyłeś 2 z 2/ })).toBeVisible({
    timeout: 30_000,
  })
  await shot(page, '8-podsumowanie')
})

test('zrzut: panel nauczyciela', async ({ page }) => {
  test.setTimeout(120_000)

  await page.goto('/')
  const teacher = page.getByRole('button', { name: /nauczyciel/i }).first()
  await teacher.click()
  await page.waitForTimeout(800)
  await shot(page, '9-panel-nauczyciela')
})
