<template>
  <GenericPage
    :get-entities
    :empty
    :verify="
      !store.state.shareView && {
        data: {
          write: 1,
          upload: 1,
        },
      }
    "
  />
</template>

<script setup>
import GenericPage from '@/components/GenericPage.vue'
import { getPersonal, getShared } from '@/resources/files'
import { useStore } from 'vuex'
import { allUsers } from '@/resources/permissions'
import LucideHome from '~icons/lucide/home'
import { computed } from 'vue'

const store = useStore()
store.commit('setCurrentFolder', { name: '', team: '' })
allUsers.fetch(null)

const getEntities = computed(() =>
  store.state.shareView ? getShared : getPersonal
)
const empty = computed(() =>
  store.state.shareView
    ? {
        icon: LucideUsers,
        title: 'No shared files',
        description: 'You can share files easily on Drive - try it out!',
      }
    : {
        icon: LucideHome,
        title: 'No files yet',
        description: 'Upload to get started!',
      }
)
</script>
