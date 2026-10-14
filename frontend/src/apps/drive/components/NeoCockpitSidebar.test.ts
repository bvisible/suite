// //// Neoffice — added file (no upstream equivalent): the cockpit that replaces the Drive's native Sidebar still
// //// fetches what that Sidebar fetched, or the pages that read it wait forever (a folder's breadcrumb of grey
// //// placeholders, neoffice-maintenance#1536 follow-up).
import { createApp, defineComponent, h } from 'vue'
import { describe, expect, it, vi } from 'vitest'

const fetched = vi.hoisted(() => ({ root: vi.fn(), storage: vi.fn(), notifications: vi.fn() }))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/shell/NeoCockpitBridge.vue', () => ({ default: defineComponent({ render: () => h('div') }) }))
vi.mock('@/apps/drive/components/Settings/SettingsDialog.vue', () => ({
  default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/stores/root', () => ({ useRootStore: () => ({ paletteOpen: false }) }))
vi.mock('@/apps/drive/components/Sidebar.vue', () => ({ default: defineComponent({ render: () => h('div') }) }))
vi.mock('@/apps/drive/data/breadcrumbs', () => ({ getRootSection: () => ({}) }))
vi.mock('@/apps/drive/emitter', () => ({ default: { on: vi.fn(), emit: vi.fn() } }))
vi.mock('@/apps/drive/resources/files', () => ({
  rootInfo: { fetch: fetched.root, data: null },
  storageBar: { fetch: fetched.storage, data: null },
}))
vi.mock('@/apps/drive/resources/permissions', () => ({
  notifCount: { fetch: fetched.notifications, data: 0 },
}))
vi.mock('@/apps/drive/utils/format', () => ({ base2BlockSize: vi.fn(), formatSize: vi.fn() }))

import NeoCockpitSidebar from './NeoCockpitSidebar.vue'

describe('NeoCockpitSidebar', () => {
  it("fetches the caller's home and the site folder, as the native Sidebar did, for the breadcrumbs", () => {
    window.__ = (message: string) => message
    const app = createApp(defineComponent({ setup: () => () => h(NeoCockpitSidebar) }))
    app.mount(document.createElement('div'))
    expect(fetched.root).toHaveBeenCalled()
    expect(fetched.storage).toHaveBeenCalled()
    expect(fetched.notifications).toHaveBeenCalled()
    app.unmount()
  })
})
