<template>
  <div class="flex h-full justify-center overflow-auto bg-surface-base pt-24 pb-14">
    <div class="flex w-full max-w-sm flex-col px-4">
      <img
        v-if="step !== 2"
        :src="suiteLogo"
        alt="Frappe Suite logo"
        class="mb-[22px] size-10"
        :class="{ invisible: step === 0 }"
        draggable="false"
      />
      <div
        v-else
        class="mb-[22px] flex size-10 items-center justify-center rounded-[13px] bg-surface-gray-2"
      >
        <Check class="size-6 text-ink-gray-8" :stroke-width="2.5" />
      </div>
      <h1 class="text-4xl-semibold text-ink-gray-9">{{ title }}</h1>
      <p class="mt-2 text-base text-ink-gray-6">{{ subtitle }}</p>

      <div class="mt-6 h-28">
        <div v-if="step === 0" class="flex h-full items-start justify-between">
          <Tooltip v-for="app in apps" :key="app.id" :text="app.name">
            <img :src="app.logo" :alt="`${app.name} logo`" class="size-[38px] object-contain" draggable="false" />
          </Tooltip>
        </div>

        <template v-else-if="step === 1">
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
        </template>

      </div>

      <Button
        v-if="step === 0"
        class="w-full"
        variant="solid"
        label="Get started"
        icon-right="lucide-chevron-right"
        @click="onPrimary"
      />

      <div v-else-if="step === 1" class="flex items-center justify-between">
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
          class="w-full"
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
import { Check } from 'lucide-vue-next'
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
