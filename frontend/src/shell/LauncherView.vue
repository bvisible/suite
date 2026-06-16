<template>
  <!-- '/suite' launcher: brand-logo app switcher for all 7 suite apps. -->
  <div class="h-full overflow-auto">
    <div class="mx-auto flex min-h-full max-w-5xl flex-col px-6 pt-[10%] pb-16">

      <div class="mx-auto grid grid-cols-4 gap-x-20 gap-y-10">
        <div class=" col-span-4">
          <TextInput placeholder="Search" variant="subtle">
            <template #prefix><span class="lucide-search size-4 text-ink-gray-4" /></template>
            </TextInput>

        </div>
        <router-link
          v-for="app in apps"
          :key="app.id"
          :to="app.prefix"
          class="group flex flex-col items-center text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          <div class="flex size-[3.375rem] items-center justify-center">
            <img
              :src="app.logo"
              :alt="`${app.name} logo`"
              class="size-[3.375rem] object-contain"
              draggable="false"
            />
          </div>
          <div class="mt-3 text-sm-medium leading-none text-ink-gray-9">{{ app.name }}</div>
        </router-link>

        <a
          href="/app/user-settings"
          class="group flex flex-col items-center text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          <div class="flex size-[3.375rem] items-center justify-center">

<svg class="size-[3.375rem]" width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M0 14.4C0 9.35953 0 6.83929 0.980941 4.91409C1.8438 3.22063 3.22063 1.8438 4.91409 0.980941C6.83929 0 9.35953 0 14.4 0H21.6C26.6405 0 29.1607 0 31.0859 0.980941C32.7794 1.8438 34.1562 3.22063 35.0191 4.91409C36 6.83929 36 9.35953 36 14.4V21.6C36 26.6405 36 29.1607 35.0191 31.0859C34.1562 32.7794 32.7794 34.1562 31.0859 35.0191C29.1607 36 26.6405 36 21.6 36H14.4C9.35953 36 6.83929 36 4.91409 35.0191C3.22063 34.1562 1.8438 32.7794 0.980941 31.0859C0 29.1607 0 26.6405 0 21.6V14.4Z" fill="#6B1FE6"/>
<path d="M22.4999 10.9286H26.3571C27.4222 10.9286 28.2857 11.792 28.2857 12.8571V24.4286C28.2857 25.4937 27.4222 26.3571 26.3571 26.3571H9.64281C8.57769 26.3571 7.71423 25.4937 7.71423 24.4286V16.8424H10.2857V23.7857H25.7142V13.5H7.71423V10.9286H13.4999V9H22.4999V10.9286ZM21.2142 19.415H14.7857V16.8436H21.2142V19.415Z" fill="white"/>
</svg>

          </div>
          <div class="mt-3 text-sm-medium leading-none text-ink-gray-9">Settings</div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

import { SUITE_APPS } from '@/apps/registry'
import { useRootStore } from '@/stores/root'
import { TextInput } from 'frappe-ui'

const apps = SUITE_APPS

onMounted(() => {
  useRootStore().setActiveApp(null)
})
</script>
