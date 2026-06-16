<template>
  <div class="flex h-screen flex-col bg-surface-base">
    <!-- Top-nav: hidden on the '/suite' launcher (which is its own full-screen
         app switcher); shown inside every app with brand-logo tabs. -->
    <header
      v-if="!isLauncher"
      class="flex h-12 shrink-0 items-center gap-1 border-b border-outline-gray-2 px-3"
    >
      <router-link
        to="/suite"
        title="Suite launcher"
        class="mr-1 flex items-center rounded px-2 py-1 text-sm-semibold text-ink-gray-9 hover:bg-surface-gray-2"
      >
        Suite
      </router-link>

      <nav class="flex items-center gap-0.5 overflow-x-auto">
        <router-link
          v-for="app in apps"
          :key="app.id"
          :to="app.prefix"
          class="flex shrink-0 items-center gap-1.5 rounded px-2 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
          :class="{ 'bg-surface-gray-3 text-ink-gray-9': isActive(app.prefix) }"
        >
          <img :src="app.logo" alt="" aria-hidden="true" class="size-4 object-contain" />
          {{ app.name }}
        </router-link>
      </nav>
    </header>

    <main class="min-h-0 flex-1 overflow-auto">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { SUITE_APPS } from '@/apps/registry'

const apps = SUITE_APPS
const route = useRoute()

const isLauncher = computed(
  () => route.path === '/suite' || route.meta.isShell === true,
)

const isActive = (prefix: string) =>
  route.path === prefix || route.path.startsWith(prefix + '/')
</script>
