<template>
  <div class="flex h-full justify-center overflow-auto bg-surface-base pt-24 pb-14">
    <div class="w-full max-w-sm px-4">
      <h1 class="text-4xl-semibold text-ink-gray-9">Welcome to Frappe Suite</h1>
      <p class="mt-2 text-base text-ink-gray-6">Everything your team needs, all in one place.</p>

      <div class="mt-6 flex justify-between">
        <Tooltip v-for="app in apps" :key="app.id" :text="app.name">
          <img :src="app.logo" :alt="`${app.name} logo`" class="size-10 object-contain" draggable="false" />
        </Tooltip>
      </div>

      <Button
        class="mt-20 w-full"
        variant="solid"
        label="Get started"
        icon-right="lucide-chevron-right"
        @click="getStarted"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'

import { SUITE_APPS } from '@/apps/registry'

const apps = SUITE_APPS

function getStarted() {}
</script>
