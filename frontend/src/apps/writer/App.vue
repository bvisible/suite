<script setup lang="ts">
import { provide } from 'vue'
import { allUsers } from 'frappe-ui/frappe/drive/js/resources'
import { FrappeUIProvider } from 'frappe-ui'
const inIframe = window.self !== window.top
provide('inIframe', inIframe)
allUsers.fetch()
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
