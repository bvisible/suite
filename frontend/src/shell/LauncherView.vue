<template>
  <!-- '/suite' launcher: brand-logo app switcher for all 7 suite apps. -->
  <div class="flex h-screen bg-surface-base">
    <!-- //// Neoffice — the cockpit rail on the /suite hub. Upstream's launcher is a
         bare centered grid; ours carries the same chrome as every other Neoffice
         surface (global search, module switcher, NORA). contextNav is empty on
         purpose: this page IS the hub. //// -->
    <NeoCockpitBridge :surface-app="surfaceApp" :navigate="(r: string) => router.push(r)" />

    <div class="flex min-w-0 flex-1 flex-col">
    <header class="flex h-12 shrink-0 items-center justify-between border-b p-2">
      <div v-if="workspaceName" class="flex items-center gap-2">
        <Avatar :image="workspaceLogo" :label="workspaceName" shape="square" size="lg" />
        <div class="text-md-medium">{{ workspaceName }}</div>
      </div>
      <div v-else />

      <Dropdown :options="userMenuOptions" align="end">
        <button
          class="flex rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          :aria-label="__('User menu')"
        >
          <Avatar :image="imageURL" :label="fullName" size="lg" />
        </button>
      </Dropdown>
    </header>

    <div class="flex-1 overflow-auto">
      <div class="mx-auto flex min-h-full max-w-5xl flex-col px-6 pt-[8%] pb-16">
        <div class="mx-auto grid grid-cols-3 gap-x-10 gap-y-10 min-[480px]:grid-cols-4 min-[480px]:gap-x-20">
          <!-- //// Neoffice — two tile kinds upstream does not have: `external` leaves
               the SPA entirely (plain <a>, e.g. Mail -> /app/webmail) and `createsOffice`
               creates a blank Office file in Drive and opens it in Collabora, in place of
               the native Writer/Sheets/Slides editors. Upstream's LauncherTile already
               renders a RouterLink, an <a> or a <button> depending on which of to/href is
               set, so the three cases share one component. //// -->
          <LauncherTile
            v-for="app in apps"
            :key="app.id"
            :to="app.external || app.createsOffice ? undefined : app.prefix"
            :href="app.external || undefined"
            :logo="app.logo"
            :label="creating === app.id ? __('Creating…') : app.name"
            @click="app.createsOffice && createOfficeFile(app)"
          />

          <LauncherTile :logo="settingsLogo" :label="__('Settings')" @click="openSettings()" />
        </div>
      </div>
    </div>

      <!-- //// Neoffice — one indent level deeper and an extra </div>: the page is now
           //// split into the cockpit rail and a content column (see the top of the
           //// template), so the dialog closes the column, not the page. //// -->
      <SuiteSettingsDialog />
    </div>
  </div>
</template>

<script setup lang="ts">
//// Neoffice — ref and useRouter added for the Office-file tiles below
//// (createOfficeFile navigates to the new document once Drive has created it).
import { h, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Avatar, Dropdown } from 'frappe-ui'
import { CircleUser, LogOut } from 'lucide-vue-next'

import { SUITE_APPS, SUITE_LOGO } from '@/apps/registry'
import type { SuiteApp } from '@/apps/registry'
//// Neoffice — the shared cockpit rail (see the template).
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import settingsLogo from '@/assets/app-logos/settings.svg'
import { useCurrentUser, useSessionStore } from '@/boot/session'
import { useThemeMenuOption } from '@/composables/useThemeMenuOption'
import LauncherTile from '@/shell/LauncherTile.vue'
import SuiteSettingsDialog from '@/shell/settings/SuiteSettingsDialog.vue'
import { openSettings } from '@/shell/settings/useSettingsDialog'
import { useWorkspace } from '@/shell/useWorkspace'
import { useRootStore } from '@/stores/root'
import { setupTheme } from '@/utils/setupTheme'

const apps = SUITE_APPS
//// Neoffice — used by createOfficeFile and by the cockpit rail's navigate prop.
const router = useRouter()

const { workspaceName, workspaceLogo } = useWorkspace()

const { fullName, imageURL } = useCurrentUser()
const sessionStore = useSessionStore()

const userMenuOptions = [
  {
    label: __('My Profile'),
    icon: h(CircleUser, { class: 'stroke-[1.5]' }),
    onClick: () => openSettings('profile'),
  },
  useThemeMenuOption(),
  {
    label: __('Log out'),
    icon: h(LogOut, { class: 'stroke-[1.5]' }),
    onClick: () => sessionStore.logout.submit(),
  },
]

onMounted(() => {
  setupTheme()
  useRootStore().setActiveApp(null)
  document.documentElement.style.overscrollBehavior = 'none'
})

onUnmounted(() => {
  document.documentElement.style.overscrollBehavior = ''
})

// //// Neoffice: identity of the hub in the cockpit module switcher ////
const surfaceApp = { name: 'suite', title: 'Suite', logo: SUITE_LOGO }

// //// Neoffice: create a blank Office file (Collabora-backed) from a tile.
// Falls back to the Drive home when the user has no team yet (onboarding). ////
const creating = ref<string | null>(null)
async function createOfficeFile(app: SuiteApp) {
  if (creating.value) return
  creating.value = app.id
  try {
    const names: Record<string, string> = { docx: __('New document'), xlsx: __('New spreadsheet'), pptx: __('New presentation') }
    const res = await fetch('/api/method/suite.drive.wopi.editor.create_office_file', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': (window as any).csrf_token || '',
      },
      body: JSON.stringify({ file_type: app.createsOffice, title: names[app.createsOffice!] }),
    })
    const { message } = await res.json()
    if (res.ok && message?.file_id) {
      router.push(`/drive/g/${message.file_id}`)
    } else {
      // No team yet (or Collabora off): let the Drive onboarding take over
      router.push('/drive')
    }
  } catch {
    router.push('/drive')
  } finally {
    creating.value = null
  }
}
</script>
