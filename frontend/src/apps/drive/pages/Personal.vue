<template>
  <GenericPage :get-entities="getPersonal" :empty="{
    icon: LucideHome,
    title: 'No files yet',
    description: 'Upload to get started!',
  }" :verify="!store.state.shareView && {
          data: {
            write: 1,
            upload: 1,
          },
        }
        " />
</template>

<script setup>
import GenericPage from '@/apps/drive/components/GenericPage.vue'
import { getPersonal } from '@/apps/drive/resources/files'
import store from '@/apps/drive/store'
import LucideHome from '~icons/lucide/home'

store.commit('setCurrentFolder', { name: '', team: '' })
</script>
