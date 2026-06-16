<template>
  <GenericPage :get-entities :empty />
</template>

<script setup>
import GenericPage from '@/apps/drive/components/GenericPage.vue'
import { computed } from 'vue'
import { getSiteFiles, getShared } from '@/apps/drive/resources/files'
import store from '@/apps/drive/store'
import LucideFiles from '~icons/lucide/files'


const getEntities = computed(() =>
  store.state.shareView ? getShared : getSiteFiles
)
const empty = computed(() =>
  store.state.shareView
    ? {
      icon: LucideUsers,
      title: 'No shared files',
      description: 'You can share files easily on Drive - try it out!',
    }
    : {
      icon: LucideFiles,
      title: 'No files on site yet',
      description: 'Upload to get started!',
    }
)
</script>
