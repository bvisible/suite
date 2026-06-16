<template>
  <!-- '/suite' launcher: brand-logo app switcher for all 7 suite apps. -->
  <div class="h-full overflow-auto bg-surface-gray-1">
    <div class="mx-auto flex min-h-full max-w-5xl flex-col justify-center px-6 py-16">
      <header class="mb-12 text-center">
        <h1 class="text-3xl font-semibold tracking-tight text-ink-gray-9">
          Frappe Suite
        </h1>
        <p class="mt-2 text-base text-ink-gray-6">
          Your workspace apps, all in one place.
        </p>
      </header>

      <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <router-link
          v-for="app in apps"
          :key="app.id"
          :to="app.prefix"
          class="group flex flex-col items-center gap-3 rounded-xl border border-outline-gray-1 bg-surface-white p-6 text-center shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:border-outline-gray-2 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
        >
          <div
            class="flex size-16 items-center justify-center rounded-2xl bg-surface-gray-2 ring-1 ring-inset ring-outline-gray-1 transition-colors group-hover:bg-surface-white"
          >
            <img
              :src="app.logo"
              :alt="`${app.name} logo`"
              class="size-10 object-contain"
              draggable="false"
            />
          </div>
          <div>
            <div class="text-base font-medium text-ink-gray-9">{{ app.name }}</div>
            <div class="mt-0.5 text-sm text-ink-gray-6">{{ app.description }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

import { SUITE_APPS } from '@/apps/registry'
import { useRootStore } from '@/stores/root'

const apps = SUITE_APPS

onMounted(() => {
  useRootStore().setActiveApp(null)
})
</script>
