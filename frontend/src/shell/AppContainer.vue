<template>
  <!-- Host for a per-app route group. Sets the active app in the root store and
       renders the app's nested <router-view>. A per-app port may replace this
       container with its own app-level layout (sidebar/toolbar) by pointing the
       group's component at its own shell in src/apps/<id>/routes.ts. -->
  <router-view />
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'

import { useRootStore } from '@/stores/root'

const route = useRoute()
const root = useRootStore()

watch(
  () => route.meta.appId as string | undefined,
  (appId) => root.setActiveApp(appId ?? null),
  { immediate: true },
)
</script>
