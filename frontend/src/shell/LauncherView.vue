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
               creates a blank Office file in Drive and opens it in its Craft editor, in place of
               the native Writer/Sheets/Slides editors. Upstream's LauncherTile already
               renders a RouterLink, an <a> or a <button> depending on which of to/href is
               set, so the three cases share one component. The label goes through __():
               Calendar and Mail read Calendrier and Messagerie, as on the cockpit's tiles. //// -->
          <LauncherTile
            v-for="app in apps"
            :key="app.id"
            :to="app.external || app.createsOffice ? undefined : app.prefix"
            :href="app.external || undefined"
            :logo="app.logo"
            :label="creating === app.id ? __('Creating…') : __(app.name)"
            @click="app.createsOffice && createOfficeFile(app)"
          />

          <LauncherTile :logo="settingsLogo" :label="__('Settings')" @click="openSettings()" />
        </div>
      </div>
    </div>

      <!-- //// Neoffice — one indent level deeper and an extra </div>: the page is now
           //// split into the cockpit rail and a content column (see the top of the
           //// template), so the dialog closes the column, not the page. //// -->
      <SuiteSettingsDialog v-model:open="showSettings" v-model:tab="settingsTab" />
    </div>
  </div>
</template>

<script setup lang="ts">
//// Neoffice — `ref` added for the Office-file tiles below (createOfficeFile keeps which tile is busy).
import { h, onMounted, onUnmounted, ref } from 'vue'
import { Avatar, Dropdown, toast } from 'frappe-ui'
import { CircleUser, LogOut } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

//// Neoffice — SUITE_LOGO too: the hub's mark in the cockpit's module switcher (surfaceApp below).
import { SUITE_APPS, SUITE_LOGO } from '@/apps/registry'
import { useStartMeeting } from '@/apps/meet/composables/useStartMeeting'
//// Neoffice — the shared cockpit rail (see the template).
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import settingsLogo from '@/assets/app-logos/settings.svg'
import { useCurrentUser, useSessionStore } from '@/boot/session'
import { useThemeMenuOption } from '@/composables/useThemeMenuOption'
import LauncherTile from '@/shell/LauncherTile.vue'
import SuiteSettingsDialog from '@/shell/settings/SuiteSettingsDialog.vue'
import { openSettings, settingsTab, showSettings } from '@/shell/settings/useSettingsDialog'
import { useWorkspace } from '@/shell/useWorkspace'
import { useRootStore } from '@/stores/root'
import { setupTheme } from '@/utils/setupTheme'

const apps = SUITE_APPS
const router = useRouter()
const root = useRootStore()
const { fullName, imageURL } = useCurrentUser()
const { startMeeting } = useStartMeeting()

const composeMail = () => router.push({ path: '/mail', query: { compose: '1' } })

const startInstantMeeting = () => startMeeting('open')

const createCalendarEvent = async () => {
  const { userStore } = await import('@/apps/calendar/stores/user')
  const calendarStore = userStore()
  try {
    if (!calendarStore.userResource.data) await calendarStore.userResource.fetch()
    if (!calendarStore.accountId) {
      toast.error('Set up Calendar before creating an event.')
      return
    }
    await router.push({ path: '/calendar', query: { new: '1' } })
  } catch {
    toast.error('Could not load Calendar account.')
  }
}

const unregisterPaletteGroups = root.registerPaletteGroups('suite-launcher', () => [
  {
    commands: [
      {
        id: 'suite-compose-mail',
        label: 'Compose mail',
        enterHint: 'compose mail',
        icon: 'lucide-pencil',
        keywords: ['new', 'email', 'message'],
        run: composeMail,
      },
      {
        id: 'suite-start-instant-meet',
        label: 'Start instant meet',
        enterHint: 'start instant meet',
        icon: 'lucide-zap',
        keywords: ['new', 'open', 'meeting'],
        run: startInstantMeeting,
      },
      {
        id: 'suite-new-event',
        label: 'New event',
        enterHint: 'create event',
        icon: 'lucide-calendar-plus',
        keywords: ['create', 'calendar'],
        run: createCalendarEvent,
      },
      {
        id: 'suite-new-sheet',
        label: 'New sheet',
        enterHint: 'create sheet',
        icon: 'lucide-table-2',
        keywords: ['create', 'spreadsheet', 'sheets'],
        run: () => router.push('/sheets/new'),
      },
      {
        id: 'suite-new-presentation',
        label: 'New presentation',
        enterHint: 'create presentation',
        icon: 'lucide-presentation',
        keywords: ['create', 'slides'],
        run: () => router.push('/slides/presentation/new'),
      },
      {
        id: 'suite-settings',
        label: 'Settings',
        shortcut: 'Mod+Shift+Comma',
        enterHint: 'open settings',
        icon: 'lucide-settings',
        keywords: ['account', 'personal', 'preferences', 'workspace'],
        run: () => openSettings(),
      },
    ],
  },
])

const { workspaceName, workspaceLogo } = useWorkspace()

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
  document.documentElement.style.overscrollBehavior = 'none'
})

onUnmounted(() => {
  document.documentElement.style.overscrollBehavior = ''
  unregisterPaletteGroups()
})

// //// Neoffice: identity of the hub in the cockpit module switcher ////
const surfaceApp = { name: 'suite', title: 'Suite', logo: SUITE_LOGO }

//// Neoffice — upstream's registry no longer exports the `SuiteApp` interface (unused-export cleanup, #834): the
//// type of a tile is read off the list instead, so the registry keeps no extra export.
type SuiteApp = (typeof SUITE_APPS)[number]

// //// Neoffice: create a blank Office file (opened in a Craft editor) from a tile.
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
      // No team yet (or the creation failed): let the Drive onboarding take over
      router.push('/drive')
    }
  } catch {
    router.push('/drive')
  } finally {
    creating.value = null
  }
}
</script>
