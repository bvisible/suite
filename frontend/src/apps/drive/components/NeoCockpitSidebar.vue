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
  <SettingsDialog v-if="!failed && showSettings" v-model="showSettings" :suggested-tab="suggestedTab" />
  <ShortcutsDialog v-if="!failed && showShortcuts" v-model="showShortcuts" />
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import driveLogo from '@/assets/app-logos/drive.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import SettingsDialog from '@/apps/drive/components/Settings/SettingsDialog.vue'
import ShortcutsDialog from '@/apps/drive/components/ShortcutsDialog.vue'
import Sidebar from '@/apps/drive/components/Sidebar.vue'
import { getRootSection } from '@/apps/drive/data/breadcrumbs'
import emitter from '@/apps/drive/emitter'
import { storageBar } from '@/apps/drive/resources/files'
import { notifCount } from '@/apps/drive/resources/permissions'
import { base2BlockSize, formatSize } from '@/apps/drive/utils/format'

const router = useRouter()
const failed = ref(false)

notifCount.fetch()
storageBar.fetch()

const showSettings = ref(false)
const showShortcuts = ref(false)
const suggestedTab = ref(0)
emitter.on('showSettings', (val = 0) => {
  if (val === -1) showSettings.value = false
  else {
    showSettings.value = true
    suggestedTab.value = val
  }
})
emitter.on('toggleShortcuts', () => {
  showShortcuts.value = !showShortcuts.value
})

function openSearch() {
  emitter.emit('showSearchPopup', true)
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
  const limit = storageBar.data.limit || 5368709120
  const used = storageBar.data.total_size || 0
  return {
    label: __('Storage'),
    sub: formatSize(used) + ' / ' + base2BlockSize(limit),
    percent: Math.min(100, (100 * used) / limit),
    onClick: () => emitter.emit('showSettings', 2),
  }
})
</script>
