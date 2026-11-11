import { describe, expect, it } from 'vitest'

import router from './index'

describe('suite route table', () => {
  it.each([
    ['/drive', 'drive-Home'],
    ['/slides', 'slides-home'],
    ['/writer', 'writer-home'],
    ['/sheets/new', 'sheets-editor'],
    ['/meet/room-1', 'meet-meeting'],
    ['/mail/login', 'mail-login'],
    ['/calendar', 'calendar-root-shortcut'],
  ])('resolves %s before any navigation', (path, name) => {
    expect(router.resolve(path).name).toBe(name)
  })

  it.each(['/slides/presentation/demo', '/writer/w/demo', '/meet/demo', '/mail/login'])(
    'exposes guest metadata immediately for %s',
    (path) => {
      expect(router.resolve(path).meta.allowGuest).toBe(true)
    },
  )

  it('does not register placeholder routes', () => {
    expect(router.getRoutes().some((route) => String(route.name).endsWith('-placeholder'))).toBe(false)
  })

  it('starts the installed suite in the app it was last in', () => {
    // resolve() reports the record, not where its redirect leads; ask the redirect.
    const start = router.getRoutes().find((route) => route.name === 'suite-start')!
    const redirect = start.redirect as (to: unknown) => string
    localStorage.setItem('suite:last-app', 'calendar')
    expect(redirect(router.resolve('/suite/start'))).toBe('/calendar')
    localStorage.removeItem('suite:last-app')
    expect(redirect(router.resolve('/suite/start'))).toBe('/mail')
  })

  //// Neoffice — the sidebar's "Shared" opens Home on its "Shared with you" tab, not on your own files (#1194)
  it('opens the shared tab of the Drive home from /drive/shared', async () => {
    const { shareView } = await import('@/apps/drive/data/prefs')
    shareView.value = false
    const shared = router.getRoutes().find((route) => route.path === '/drive/shared')!
    const redirect = shared.redirect as (to: unknown) => unknown
    expect(redirect(router.resolve('/drive/shared'))).toEqual({ name: 'drive-Home' })
    expect(shareView.value).toBe(true)
  })

  it('keeps the runtime load error available to guests', () => {
    expect(router.resolve('/suite/load-error').meta.allowGuest).toBe(true)
  })
})
