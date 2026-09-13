<template>
  <!-- //// Neoffice — the empty states come from the script, where they are translated -->
  <GenericPage :get-entities="shareView ? getShared : getPersonal" :empty="shareView ? emptyShared : emptyPersonal" :verify="!shareView && {
          data: {
            write: 1,
            upload: 1,
          },
        }
        " />
</template>

<script setup>
import { computed } from 'vue' //// Neoffice — for the translated empty states below
import GenericPage from '@/apps/drive/components/GenericPage.vue'
import { getPersonal, getShared } from '@/apps/drive/resources/files'
import { shareView } from '@/apps/drive/data/prefs'
import { setCurrentFolder } from '@/apps/drive/data/currentFolder'
import LucideHome from '~icons/lucide/home'
import LucideUsers from '~icons/lucide/users'

//// Neoffice — upstream wrote these empty states as plain English literals in the
//// template, so the Drive home of every non-English site said "No files yet".
//// Computed, so the texts are read once the catalog is loaded, not at setup.
const emptyShared = computed(() => ({
  icon: LucideUsers,
  title: __('No shared files'),
  description: __('You can share files easily on Drive - try it out!'),
}))
const emptyPersonal = computed(() => ({
  icon: LucideHome,
  title: __('No files yet'),
  description: __('Upload to get started!'),
}))

setCurrentFolder({ name: '' })
</script>
