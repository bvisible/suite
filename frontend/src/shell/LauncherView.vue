<template>
  <!-- '/suite' launcher: brand-logo app switcher for all 7 suite apps. -->
  <div class="h-full overflow-auto">
    <div class="mx-auto flex min-h-full max-w-5xl flex-col px-6 pt-[10%] pb-16">

      <div class="mx-auto grid grid-cols-4 gap-x-20 gap-y-10">
        <!-- //// Neoffice: tiles with `external` leave the SPA (plain <a>, e.g. Mail ->
             /webmail); tiles with `createsOffice` create a blank Office file in the
             Drive and open it in Collabora (replaces the native editors). //// -->
        <component
          :is="app.external ? 'a' : app.createsOffice ? 'button' : RouterLink"
          v-for="app in apps"
          :key="app.id"
          v-bind="app.external ? { href: app.external } : app.createsOffice ? {} : { to: app.prefix }"
          class="group flex flex-col items-center text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
          @click="app.createsOffice && createOfficeFile(app)"
        >
          <div class="flex size-[3.375rem] items-center justify-center">
            <img
              :src="app.logo"
              :alt="`${app.name} logo`"
              class="size-[3.375rem] object-contain"
              :class="{ 'opacity-50': creating === app.id }"
              draggable="false"
            />
          </div>
          <div class="mt-3 text-sm-medium leading-none text-ink-gray-9">
            {{ creating === app.id ? __('Creating…') : app.name }}
          </div>
        </component>

        <a
          href="/app/user-settings"
          class="group flex flex-col items-center text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          <div class="flex size-[3.375rem] items-center justify-center">
            <img
              :src="suiteLogo"
              alt="Settings logo"
              class="size-[3.375rem] object-contain"
              draggable="false"
            />
          </div>
          <div class="mt-3 text-sm-medium leading-none text-ink-gray-9">Settings</div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
// //// Neoffice: RouterLink imported for the dynamic <component :is> above ////
import { RouterLink, useRouter } from 'vue-router'

import { SUITE_APPS, SUITE_LOGO } from '@/apps/registry'
import type { SuiteApp } from '@/apps/registry'
import { useRootStore } from '@/stores/root'

const apps = SUITE_APPS
const suiteLogo = SUITE_LOGO
const router = useRouter()

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

onMounted(() => {
  useRootStore().setActiveApp(null)
})
</script>
