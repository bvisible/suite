<template>
  <div class="flex h-full justify-center overflow-auto bg-surface-base pt-24 pb-14">
    <div class="w-full max-w-sm px-4">
      <img
        :src="suiteLogo"
        alt="Frappe Suite logo"
        class="mb-[22px] size-10"
        :class="{ invisible: step === 0 }"
        draggable="false"
      />
      <h1 class="text-4xl-semibold text-ink-gray-9">{{ title }}</h1>
      <p class="mt-2 text-base text-ink-gray-6">{{ subtitle }}</p>

      <div v-if="step === 0" class="mt-6 flex justify-between">
        <Tooltip v-for="app in apps" :key="app.id" :text="app.name">
          <img :src="app.logo" :alt="`${app.name} logo`" class="size-[38px] object-contain" draggable="false" />
        </Tooltip>
      </div>

      <div v-else-if="step === 1" class="mt-6">
        <FormControl
          v-model="emails"
          type="textarea"
          variant="outline"
          :rows="3"
          class="!resize-none"
          placeholder="name@company.com, another@company.com"
          :disabled="loading"
        />
        <ErrorMessage class="mt-2" :message="invite.error" />
      </div>

      <Button
        v-if="step === 0"
        class="mt-20 w-full"
        variant="solid"
        label="Get started"
        icon-right="lucide-chevron-right"
        @click="onPrimary"
      />

      <div v-else-if="step === 1" class="mt-8 flex items-center justify-between">
        <Button variant="ghost" label="Skip for now" :disabled="loading" @click="skip" />
        <Button
          variant="solid"
          label="Send Invites"
          :loading="loading"
          @click="sendInvites"
        />
      </div>

      <template v-else>
        <Button
          class="mt-20 w-full"
          variant="solid"
          label="Open Suite"
          :loading="markComplete.loading"
          @click="markComplete.submit()"
        />
        <ErrorMessage class="mt-3" :message="markComplete.error" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, ErrorMessage, FormControl, Tooltip, createResource } from 'frappe-ui'

import { SUITE_APPS, SUITE_LOGO } from '@/apps/registry'

const apps = SUITE_APPS
const suiteLogo = SUITE_LOGO

const step = ref(0)
const emails = ref('')

const copy = [
  { title: 'Welcome to Frappe Suite', subtitle: 'Everything your team needs, all in one place.' },
  { title: "Let's invite your team", subtitle: 'Add teammates and explore Suite together.' },
  { title: "You're all set!", subtitle: 'Your workspace is ready. Time to dive in.' },
]
const title = computed(() => copy[step.value].title)
const subtitle = computed(() => copy[step.value].subtitle)

// Full reload so the router's cached setup state refetches and routes to /suite.
const markComplete = createResource({
  url: 'suite.api.account.mark_setup_complete',
  onSuccess: () => {
    window.location.href = '/suite'
  },
})

const invite = createResource({
  url: 'frappe.core.api.user_invitation.invite_by_email',
  onSuccess: () => {
    step.value = 2
  },
})

const loading = computed(() => invite.loading)

function onPrimary() {
  step.value = 1
}

function sendInvites() {
  const cleaned = emails.value
    .split(/[\n,]+/)
    .map((e) => e.trim())
    .filter(Boolean)
  if (!cleaned.length) {
    skip()
    return
  }
  invite.submit({
    emails: cleaned.join(', '),
    roles: ['Drive User', 'Meet User'],
    redirect_to_path: '/suite',
    app_name: 'suite',
  })
}

function skip() {
  step.value = 2
}
</script>
