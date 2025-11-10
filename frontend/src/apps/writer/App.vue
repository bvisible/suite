<script setup lang="ts">
import { provide } from 'vue'
import { FrappeUIProvider } from 'frappe-ui'
const inIframe = window.self !== window.top
provide('inIframe', inIframe)
</script>

<template>
  <FrappeUIProvider>
    <div class="flex flex-col h-screen">
      <router-view :key="$route.fullPath" v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </div>
  </FrappeUIProvider>
</template>

<style scoped></style>
