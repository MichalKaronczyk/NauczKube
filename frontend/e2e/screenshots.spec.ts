import { test, type Page } from '@playwright/test'

/** Zrzuty 5 ekranów do README i do filmu. Uruchomienie:
 *  npx playwright test --project=chromium e2e/screenshots.spec.ts */

const OUT = '../docs/zrzuty'

async function solo(page: Page, pseudonym: string) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Ćwiczę sam' }).click()
  await page.getByLabel(/pseudonim/i).fill(pseudonym)
  await page.getByRole('button', { name: 'Zaczynamy' }).click()
}

test('zrzuty ekranów', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })

  // 1. Start
  await page.goto('/')
  await page.screenshot({ path: `${OUT}/1-start.png` })

  // 2. Tematy
  await solo(page, 'Ola')
  await page.waitForSelector('.topic-row')
  await page.screenshot({ path: `${OUT}/2-tematy.png` })

  // 3. Karta „jak to działa” — pokazuje się przy pierwszym wejściu na tablicę
  await page.locator('.topic-row', { hasText: 'Kwadrat sumy' }).click()
  await page.waitForSelector('.tutorial')
  await page.screenshot({ path: `${OUT}/3a-tutorial.png` })
  await page.getByRole('button', { name: 'Rozumiem, zaczynamy' }).click()

  // 3. Tablica
  await page.waitForSelector('.kuba-line.is-shown')
  await page.waitForTimeout(2500)
  await page.locator('.kuba-line').nth(1).click()
  await page.waitForSelector('textarea#explanation')
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/3-tablica.png` })

  // 3b. Tablica z podpowiedzią
  await page.getByRole('button', { name: /Podpowiedź/ }).click()
  await page.waitForSelector('.bubble-hint')
  await page.screenshot({ path: `${OUT}/3b-podpowiedz.png` })

  // 4. Zadanie transferowe
  await page.fill('textarea#explanation', 'Brakuje wyrazu 2ab, czyli podwojonego iloczynu.')
  await page.getByRole('button', { name: 'Wyślij' }).click()
  await page.waitForTimeout(600)
  await page.fill('textarea#explanation', 'Podstaw x = 1 i porównaj obie strony, wyjdzie inaczej.')
  await page.getByRole('button', { name: 'Wyślij' }).click()
  await page.waitForSelector('button:has-text("Dobrze zrobione")')
  await page.waitForTimeout(2600)
  await page.screenshot({ path: `${OUT}/4-transfer.png` })

  // 5. Podsumowanie
  await page.getByRole('button', { name: 'Dobrze zrobione' }).click()
  await page.waitForSelector('.summary-grid', { timeout: 20_000 })
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/5-podsumowanie.png`, fullPage: true })

  // 6. Panel nauczyciela
  await page.goto('/')
  await page.getByRole('button', { name: 'Jestem nauczycielem' }).click()
  await page.getByRole('button', { name: 'Utwórz klasę' }).click()
  await page.getByLabel(/Nazwa klasy/).fill('2B')
  await page.getByLabel(/PIN do panelu/).fill('4321')
  await page.getByRole('button', { name: 'Utwórz klasę' }).click()
  await page.waitForSelector('.teacher-summary')
  await page.screenshot({ path: `${OUT}/6-panel-nauczyciela.png`, fullPage: true })
})

test('zrzut trybu informatycznego', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await solo(page, 'Informatyk')
  await page.waitForSelector('.topic-row')
  await page.locator('.topic-row', { hasText: 'range' }).click()
  await page.getByRole('button', { name: 'Rozumiem, zaczynamy' }).click()
  await page.waitForSelector('.kuba-line.is-code')
  await page.waitForTimeout(3500)
  await page.screenshot({ path: `${OUT}/7-tryb-informatyczny.png` })
})
