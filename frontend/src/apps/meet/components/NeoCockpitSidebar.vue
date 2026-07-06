<!-- //// Neoffice: new file — Meet flavor of the shared NeoCockpit chrome.
     Mounts the Neoffice menu in Meet (Home) like the Drive does, with an
     automatic fallback to the native MeetSidebar when the chrome can't load. //// -->
<template>
  <MeetSidebar v-if="failed" />
  <NeoCockpitBridge
    v-else
    :surface-app="surfaceApp"
    :context-nav="contextNav"
    :navigate="(r) => router.push(r)"
    @failed="failed = true"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import meetLogo from '@/assets/app-logos/meet.png'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'
import MeetSidebar from '@/apps/meet/components/MeetSidebar.vue'

const route = useRoute()
const router = useRouter()
const failed = ref(false)

const surfaceApp = { name: 'meet', title: 'Meet', logo: meetLogo }

const contextNav = computed(() => [
  {
    label: 'Meet',
    items: [
      { label: __('Home'), icon: 'lucide-home', route: '/meet', active: route.name === 'meet-home' },
      { label: __('Calendar'), icon: 'lucide-calendar', route: '/calendar', active: false },
    ],
  },
])
</script>
