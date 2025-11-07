<script setup lang="ts">
import { provide } from 'vue'
const inIframe = window.self !== window.top
provide('inIframe', inIframe)
</script>

<template>
  <div class="flex flex-col h-screen">
    <router-view :key="$route.fullPath" v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </div>
</template>

<style scoped></style>
