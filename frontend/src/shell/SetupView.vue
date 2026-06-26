<template>
  <div class="flex h-full justify-center overflow-auto bg-surface-base pt-24 pb-14">
    <div class="flex w-full max-w-sm flex-col px-4">
      <svg
        class="setup-mark mb-7 size-10 shrink-0"
        :class="{ invisible: step === 'welcome', 'is-done': step === 'done' }"
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          class="setup-mark__squircle"
          d="M0 14.4C0 9.35953 0 6.83929 0.980941 4.91409C1.8438 3.22063 3.22063 1.8438 4.91409 0.980941C6.83929 0 9.35953 0 14.4 0H21.6C26.6405 0 29.1607 0 31.0859 0.980941C32.7794 1.8438 34.1562 3.22063 35.0191 4.91409C36 6.83929 36 9.35953 36 14.4V21.6C36 26.6405 36 29.1607 35.0191 31.0859C34.1562 32.7794 32.7794 34.1562 31.0859 35.0191C29.1607 36 26.6405 36 21.6 36H14.4C9.35953 36 6.83929 36 4.91409 35.0191C3.22063 34.1562 1.8438 32.7794 0.980941 31.0859C0 29.1607 0 26.6405 0 21.6V14.4Z"
        />
        <path
          class="setup-mark__glyph"
          d="M22.4999 10.9286H26.3571C27.4222 10.9286 28.2857 11.792 28.2857 12.8571V24.4286C28.2857 25.4937 27.4222 26.3571 26.3571 26.3571H9.64281C8.57769 26.3571 7.71423 25.4937 7.71423 24.4286V16.8424H10.2857V23.7857H25.7142V13.5H7.71423V10.9286H13.4999V9H22.4999V10.9286ZM21.2142 19.415H14.7857V16.8436H21.2142V19.415Z"
          fill="white"
        />
        <polyline class="setup-mark__check" points="10,18.5 15.5,23.5 26,12.5" />
      </svg>

      <div :key="step" class="setup-screen">
        <h1 class="text-4xl-semibold text-ink-gray-9">{{ current.title }}</h1>
        <p class="mt-2 text-base text-ink-gray-6">{{ current.subtitle }}</p>

        <div class="mt-6 h-28">
          <div v-if="step === 'welcome'" class="flex h-full items-start justify-between">
            <Tooltip v-for="(app, i) in apps" :key="app.id" :text="app.name">
              <img
                :src="app.logo"
                :alt="`${app.name} logo`"
                class="setup-icon size-[38px] object-contain"
                :style="{ animationDelay: `${i * 0.06}s` }"
                draggable="false"
              />
            </Tooltip>
          </div>

          <template v-else-if="step === 'invite'">
            <FormControl
              v-model="emails"
              type="textarea"
              variant="outline"
              :rows="3"
              class="!resize-none"
              placeholder="name@company.com, another@company.com"
              :disabled="invite.loading"
            />
            <ErrorMessage class="mt-2" :message="invite.error" />
          </template>
        </div>

        <Button
          v-if="step === 'welcome'"
          class="w-full"
          variant="solid"
          label="Get started"
          icon-right="lucide-chevron-right"
          @click="onPrimary"
        />

        <div v-else-if="step === 'invite'" class="flex items-center justify-between">
          <Button variant="ghost" label="Skip for now" :disabled="invite.loading" @click="skip" />
          <Button
            variant="solid"
            label="Send Invites"
            icon-right="lucide-chevron-right"
            :loading="invite.loading"
            @click="sendInvites"
          />
        </div>

        <template v-else>
          <Button
            class="w-full"
            variant="solid"
            label="Open Suite"
            icon-right="lucide-chevron-right"
            :loading="markComplete.loading"
            @click="markComplete.submit()"
          />
          <ErrorMessage class="mt-3" :message="markComplete.error" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, ErrorMessage, FormControl, Tooltip, createResource } from 'frappe-ui'

import { SUITE_APPS } from '@/apps/registry'

const apps = SUITE_APPS

type Step = 'welcome' | 'invite' | 'done'

const step = ref<Step>('welcome')
const emails = ref('')

const copy: Record<Step, { title: string; subtitle: string }> = {
  welcome: { title: 'Welcome to Frappe Suite', subtitle: 'Everything your team needs, all in one place.' },
  invite: { title: "Let's invite your team", subtitle: 'Add teammates and explore Suite together.' },
  done: { title: "You're all set!", subtitle: 'Your workspace is ready. Time to dive in.' },
}
const current = computed(() => copy[step.value])

// Full reload so the router's cached setup state refetches and routes to /suite.
const markComplete = createResource({
  url: 'suite.api.account.mark_setup_complete',
  onSuccess: () => {
    window.location.href = '/suite'
  },
})

const invite = createResource({
  url: 'suite.api.account.invite_users',
  onSuccess: () => {
    step.value = 'done'
  },
})

function onPrimary() {
  step.value = 'invite'
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
  invite.submit({ emails: cleaned.join(', ') })
}

function skip() {
  step.value = 'done'
}
</script>

<style scoped>
.setup-screen {
  animation: fadeIn 0.3s ease-out both;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(4px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.setup-icon {
  opacity: 0;
  animation: iconIn 0.6s ease both;
}

@keyframes iconIn {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.setup-mark__squircle {
  fill: #6b1fe6;
  transition: fill 300ms ease;
}

.setup-mark__glyph {
  transition: opacity 200ms ease;
}

.setup-mark__check {
  fill: none;
  stroke: var(--ink-gray-8);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity 200ms ease;
}

.setup-mark.is-done .setup-mark__squircle {
  fill: var(--surface-gray-2);
}

.setup-mark.is-done .setup-mark__glyph {
  opacity: 0;
}

.setup-mark.is-done .setup-mark__check {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .setup-screen,
  .setup-icon {
    animation: none;
    opacity: 1;
    transform: none;
  }

  .setup-mark__squircle,
  .setup-mark__glyph,
  .setup-mark__check {
    transition: none;
  }
}
</style>
