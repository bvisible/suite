<script setup lang="ts">
import { provide, onMounted } from 'vue'
import { allUsers } from 'frappe-ui/frappe/drive/js/resources'
import FDialogs from '@/components/FDialogs.vue'

import { FrappeUIProvider } from 'frappe-ui'
const inIframe = window.self !== window.top
provide('inIframe', inIframe)
allUsers.fetch()

onMounted(() => {
  const theme = localStorage.getItem('theme')
  if (['light', 'dark'].includes(theme)) {
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

<style scoped></style>
