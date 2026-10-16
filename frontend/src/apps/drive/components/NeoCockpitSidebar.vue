<!-- //// Neoffice: new file — Drive flavor of the shared NeoCockpit chrome
     (ported from the drive fork onto the unified suite SPA). Falls back to
     the native Sidebar automatically when the chrome cannot mount. //// -->
<template>
  <Sidebar v-if="failed" />
  <NeoCockpitBridge
    v-else
    :surface-app="surfaceApp"
    :context-nav="contextNav"
    :context-footer="contextFooter"
    :navigate="(r) => router.push(r)"
    :on-search="openSearch"
    search-kbd="⌘K"
    @failed="failed = true"
  />
  <!-- //// Neoffice — upstream's dialog is `v-model:open` since the shell's SuiteSettingsDialog, and the shortcuts
       dialog moved to the layout (DriveLayout.vue, frappe-ui's KeyboardShortcutsDialog): this component keeps only
       the settings. //// -->
  <SettingsDialog v-if="!failed" v-model:open="showSettings" :suggested-tab="suggestedTab" />
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import driveLogo from '@/assets/app-logos/drive.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import SettingsDialog from '@/apps/drive/components/Settings/SettingsDialog.vue'
import Sidebar from '@/apps/drive/components/Sidebar.vue'
import { getRootSection } from '@/apps/drive/data/breadcrumbs'
import emitter from '@/apps/drive/emitter'
//// Neoffice — the search box opens the suite's command palette (upstream removed Drive's own SearchPopup)
import { useRootStore } from '@/stores/root'
//// Neoffice — rootInfo too: the native Sidebar fetched it, and the breadcrumbs wait for it (data/breadcrumbs.ts)
import { rootInfo, storageBar } from '@/apps/drive/resources/files'
import { storageGauge } from '@/apps/drive/utils/storageGauge'
import { notifCount } from '@/apps/drive/resources/permissions'
import { base2BlockSize, formatSize } from '@/apps/drive/utils/format'

const router = useRouter()
const failed = ref(false)

notifCount.fetch()
storageBar.fetch()
//// Neoffice — the native Sidebar fetched the caller's home and the site folder; replaced by the cockpit, nothing
//// did, and a folder opened by its link kept a breadcrumb of grey placeholders: its trail waits for them.
rootInfo.fetch()

const showSettings = ref(false)
//// Neoffice — a tab is named now ('statistics', 'webdav', 'storage'), as upstream's Sidebar and StorageBar emit it
const suggestedTab = ref('profile')
emitter.on('showSettings', (val = 'profile') => {
  if (val === -1) showSettings.value = false
  else {
    showSettings.value = true
    suggestedTab.value = val
  }
})

const root = useRootStore()
function openSearch() {
  root.paletteOpen = true
}

const surfaceApp = {
  name: 'drive',
  title: 'Drive',
  logo: driveLogo,
}

const contextNav = computed(() => {
  const rootName = getRootSection().name || ''
  const sections = [
    {
      items: [
        {
          label: __('Inbox'),
          icon: 'lucide-inbox',
          route: '/drive/inbox',
          active: rootName === 'drive-Inbox',
          badge: notifCount.data || '',
        },
      ],
    },
    {
      label: 'Drive',
      items: [
        { label: __('Home'), icon: 'lucide-home', route: '/drive', active: rootName === 'drive-Home' },
        { label: __('Recents'), icon: 'lucide-clock', route: '/drive/recents', active: rootName === 'drive-Recents' },
        { label: __('Shared'), icon: 'lucide-users', route: '/drive/shared', active: rootName === 'drive-Shared' },
        { label: __('Trash'), icon: 'lucide-trash', route: '/drive/trash', active: rootName === 'drive-Trash' },
      ],
    },
  ]
  //// Neoffice — the "Teams" section is gone with the teams themselves. Upstream's
  //// de-teaming (4df6ee65a / f3cf5206c, merged 31.08.2026) dropped Drive Team,
  //// Drive Team Member and the getTeams resource: storage is now one private
  //// folder per user under a single site root, and sharing goes through Drive
  //// Permission rows rather than team membership. Nothing replaces this section —
  //// the shared files it used to reach are under "Everyone" and "Shared".
  sections.push({
    label: __('Views'),
    items: [
      { label: __('Attachments'), icon: 'lucide-paperclip', route: '/drive/attachments', active: rootName === 'drive-Attachments' },
      { label: __('Favourites'), icon: 'lucide-star', route: '/drive/favourites', active: rootName === 'drive-Favourites' },
      { label: __('Documents'), icon: 'lucide-file-text', route: '/drive/documents', active: rootName === 'drive-Documents' },
      { label: __('Presentations'), icon: 'lucide-gallery-vertical-end', route: '/drive/presentations', active: rootName === 'drive-Presentations' },
    ],
  })
  return sections
})

const contextFooter = computed(() => {
  if (!storageBar.data) return null
  //// Neoffice — a quota, or the volume the Drive writes to, or the person's use alone (utils/storageGauge.js): the
  //// bar no longer says « / 5 GB » where there is no quota (maintenance#1598)
  const gauge = storageGauge(storageBar.data)
  return {
    label: __('Storage'),
    //// Neoffice — the quota or the volume after the person's use, and the use alone without either
    sub: gauge.limit
      ? formatSize(gauge.used) + ' / ' + (gauge.volume ? formatSize(gauge.limit) : base2BlockSize(gauge.limit))
      : formatSize(gauge.used),
    percent: gauge.percent,
    onClick: () => emitter.emit('showSettings', 'statistics'),
  }
})
</script>
