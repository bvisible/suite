<script setup lang="ts">
import { onMounted, provide } from 'vue'
import { FrappeUIProvider } from 'frappe-ui'

import FDialogs from '@/apps/writer/components/FDialogs.vue'

/**
 * Writer route-group layout.
 *
 * Maps the standalone app's root App.vue. The suite shell already provides the
 * top-level chrome, so this layout only:
 *   - provides the `inIframe` injection that Document.vue depends on,
 *   - applies the persisted light/dark theme to <html data-theme>,
 *   - wraps children in FrappeUIProvider + the writer's FDialogs host and
 *     renders the nested <router-view>.
 *
 * The standalone App.vue also called `allUsers.fetch()` / `apps.fetch()` as
 * boot side-effects; those are triggered on writer module load in routes.ts.
 */
const inIframe = window.self !== window.top
provide('inIframe', inIframe)

onMounted(() => {
  const theme = localStorage.getItem('theme')
  if (theme && ['light', 'dark'].includes(theme)) {
    document.documentElement.setAttribute('data-theme', theme)
  }
})
</script>

<template>
  <FrappeUIProvider>
    <div class="flex flex-col h-screen">
      <router-view :key="$route.fullPath" v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </div>
    <FDialogs />
  </FrappeUIProvider>
</template>
