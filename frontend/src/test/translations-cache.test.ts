// //// Neoffice — added file (no upstream equivalent): the reader's catalogue is the page's (maintenance#1392).
//
// www/suite.py puts the reader's catalogue on window.translatedMessages before any script runs. The calendar, the
// mail, Drive and Writer also keep a `translations` resource, cached in the browser for a page without one; but
// frappe-ui restores a cached resource as soon as it is created, fetched or not, and its transform put an older
// catalogue back over the page's: a new translation never showed until the browser's storage was cleared. The
// resource is made only where the page carries no catalogue — an upstream merge that brings the old pattern back
// fails here.
import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const APPS = ['calendar', 'mail', 'drive', 'writer']

describe("the page's catalogue is never replaced by a cached one", () => {
  it.each(APPS)('%s makes its translations resource only when the page has no catalogue', (app) => {
    const source = fs.readFileSync(path.resolve(__dirname, `../apps/${app}/routes.ts`), 'utf8')
    const at = source.indexOf("cache: 'translations'")
    expect(at, `${app}: no cached translations resource left`).toBeGreaterThan(-1)
    // The resource is created inside the guard, not before it
    const before = source.slice(0, at)
    const creation = before.lastIndexOf('createResource(')
    const guard = before.lastIndexOf('translatedMessages)')
    expect(guard, `${app}: the guard comes first`).toBeGreaterThan(-1)
    expect(guard, `${app}: created inside the guard`).toBeLessThan(creation)
    expect(before.slice(guard, creation)).not.toMatch(/\n\s*\n/)
    expect(source).not.toMatch(/const translations = createResource/)
  })
})
