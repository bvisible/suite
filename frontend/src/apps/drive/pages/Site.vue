<template>
  <GenericPage
    :get-entities="getSiteFiles"
    :empty="{
      icon: LucideFiles,
      title: 'No files on site',
      description: 'Once you start adding files, you\'ll see them here.',
    }"
  />
</template>

<script setup>
import GenericPage from '@/components/GenericPage.vue'

import { getSiteFiles } from '@/resources/files'
import LucideFiles from '~icons/lucide/files'
</script>
