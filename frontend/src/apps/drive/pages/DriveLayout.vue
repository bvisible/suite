<template>
  <FrappeUIProvider>
    <template v-if="isLoggedIn || $route.meta.allowGuest">
      <div v-if="$route.name === 'drive-Signup'" id="dropzone" class="h-full">
        <router-view :key="$route.fullPath" v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>
      <!-- Keep sticky page chrome below dialogs portalled to body. -->
      <DesktopShell v-else-if="isDesktop" :scroll="shellScroll" class="isolate">
        <template v-if="normalView" #sidebar>
          <!-- //// Neoffice — the shared NeoCockpit chrome takes the place of Drive's
               native sidebar, so Drive, Calendar and Meet all carry the same left rail
               as the rest of Neoffice. It falls back to <Sidebar /> on its own when the
               chrome cannot mount (see NeoCockpitSidebar.vue), so this slot is never
               left empty. Before the merge we mounted it beside the layout; upstream's
               frappe-ui app shells (53bc173f6) own the sidebar slot now, so it belongs
               here instead. //// -->
          <NeoCockpitSidebar />
        </template>
        <div id="dropzone" class="relative flex min-h-full flex-col bg-surface-base" :class="{ 'h-full': !shellScroll }">
          <router-view :key="$route.fullPath" v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </div>
      </DesktopShell>
      <MobileShell v-else class="isolate">
        <div id="dropzone" class="relative flex min-h-full flex-col bg-surface-base" :class="{ 'h-full': !shellScroll }">
          <router-view :key="$route.fullPath" v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </div>
        <template v-if="!inIframe && isLoggedIn" #nav>
          <BottomBar />
        </template>
      </MobileShell>
    </template>
    <router-view v-else :key="$route.fullPath" v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
    <button accesskey="u" class="hidden" @click="emitter.emit('uploadFile')" />
    <KeyboardShortcutsDialog v-model:open="showShortcuts" />
    <FileUploader
      v-if="normalView && ['drive-Folder', 'drive-Home'].includes($route.name) && !($route.name === 'drive-Home' && shareView)" />
    <FDialogs />
  </FrappeUIProvider>
</template>
<script setup>
// //// Neoffice: NeoCockpit chrome (falls back to the native Sidebar itself) ////
import NeoCockpitSidebar from '@/apps/drive/components/NeoCockpitSidebar.vue'
import FDialogs from '@/apps/drive/components/FDialogs.vue'
import BottomBar from '@/apps/drive/components/BottomBar.vue'
import FileUploader from '@/apps/drive/components/FileUploader.vue'
import { useSessionStore } from '@/boot/session'
import { computed, onMounted, onScopeDispose, provide, ref } from 'vue'
import { sidebarCollapsed, shareView } from '@/apps/drive/data/prefs'
import { useMediaQuery } from '@vueuse/core'
import emitter from '@/apps/drive/emitter'
import { initSocket } from '@/apps/drive/socket'
import { DesktopShell, FrappeUIProvider, KeyboardShortcutsDialog, MobileShell, useKeyboardShortcut } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'
import { setupTheme } from '@/utils/setupTheme'
import { useRootStore } from '@/stores/root'
import { rootInfo } from '@/apps/drive/resources/files'
import { isApple } from '@/apps/drive/utils/files'

// Provided from the route-group layout since the suite main.ts is shared.
provide('emitter', emitter)
provide('socket', initSocket())

const route = useRoute()
const router = useRouter()
const isDesktop = useMediaQuery('(min-width: 768px)')
const shellScroll = computed(() => route.meta.shellScroll !== false)
const inIframe = window.self !== window.top
provide('inIframe', inIframe)

const showShortcuts = ref(false)
const isLoggedIn = computed(() => useSessionStore().isLoggedIn)
const normalView = computed(() => !inIframe && isLoggedIn.value)
const root = useRootStore()
const unregisterPaletteGroups = root.registerPaletteGroups('drive-layout', () => {
  if (!normalView.value) return []

  const commands = [
    {
      id: 'drive-settings',
      label: 'Settings',
      shortcut: 'Mod+Shift+Comma',
      enterHint: 'open settings',
      icon: 'lucide-settings',
      run: () => emitter.emit('showSettings'),
    },
  ]

  if (
    ['drive-Folder', 'drive-Home'].includes(String(route.name)) &&
    !(route.name === 'drive-Home' && shareView.value)
  ) {
    commands.push(
      {
        id: 'drive-new-folder',
        label: 'New folder',
        enterHint: 'create folder',
        icon: 'lucide-folder-plus',
        description: 'Create in the current Drive folder',
        keywords: ['create'],
        run: () => emitter.emit('newFolder'),
      },
      {
        id: 'drive-upload-file',
        label: 'Upload file',
        enterHint: 'upload file',
        icon: 'lucide-file-up',
        description: 'Upload to the current Drive folder',
        keywords: ['create', 'add'],
        run: () => emitter.emit('uploadFile'),
      },
    )
  }

  return commands.length ? [{ commands }] : []
})
onScopeDispose(unregisterPaletteGroups)

onMounted(() => {
  setupTheme()
})

const accessKey = (key) => {
  if (isApple()) return `Ctrl+Alt+${key}`
  if (navigator.userAgent.includes('Firefox')) return `Alt+Shift+${key}`
  return `Alt+${key}`
}

const shortcut = (combo, description, group, handler) => ({
  combo,
  description: __(description),
  group: __(group),
  enabled: normalView,
  handler,
})

useKeyboardShortcut([
  shortcut('Mod+Shift+ArrowRight', 'Expand sidebar', 'General', () => (sidebarCollapsed.value = false)),
  shortcut('Mod+Shift+ArrowLeft', 'Collapse sidebar', 'General', () => (sidebarCollapsed.value = true)),
  {
    combo: 'Shift+Slash',
    description: __('View Shortcuts'),
    group: __('General'),
    enabled: normalView,
    allowInDialog: true,
    handler: () => (showShortcuts.value = !showShortcuts.value),
  },
  shortcut(accessKey('I'), 'Inbox', 'Navigation', () => router.push({ name: 'drive-Inbox' })),
  shortcut(accessKey('H'), 'Home', 'Navigation', () => router.push({ name: 'drive-Home' })),
  shortcut(accessKey('E'), 'Everyone', 'Navigation', () => {
    if (rootInfo.data?.root) router.push({ name: 'drive-Folder', params: { entityName: rootInfo.data.root } })
  }),
  shortcut(accessKey('R'), 'Recents', 'Navigation', () => router.push({ name: 'drive-Recents' })),
  shortcut(accessKey('F'), 'Favourites', 'Navigation', () => router.push({ name: 'drive-Favourites' })),
  shortcut(accessKey('A'), 'Attachments', 'Navigation', () => router.push({ name: 'drive-Attachments' })),
  shortcut(accessKey('D'), 'Documents', 'Navigation', () => router.push({ name: 'drive-Documents' })),
  shortcut(accessKey('S'), 'Share selected file', 'List', () => emitter.emit('share')),
  shortcut(accessKey('U'), 'Upload a file', 'List', () => emitter.emit('uploadFile')),
  shortcut(accessKey('N'), 'Create a folder', 'List', () => emitter.emit('newFolder')),
])

</script>

<style>
/* //// Neoffice — the drop zone fills the pane again. Since upstream's frappe-ui app shells (53bc173f6, merged with
   //// 42afbc164 on 31.08.2026) `#dropzone` sits in the shell's scroll region inside an auto-height wrapper, so its
   //// `min-h-full` has nothing to resolve against: it is only as tall as the navbar, the toolbar and the rows, and a
   //// file dropped below the last row (most of the page of a short or empty folder) got neither the « Drop to upload »
   //// animation (`.file-drag`, GenericPage.vue) nor an upload. The wrapper is made at least as tall as the scroll
   //// viewport and #dropzone fills it. Drop this when upstream makes #dropzone fill its pane. */
[data-slot='scroll-area-viewport'] > :has(> #dropzone) {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
[data-slot='scroll-area-viewport'] > :has(> #dropzone) > #dropzone {
  flex: 1 0 auto;
}
</style>
