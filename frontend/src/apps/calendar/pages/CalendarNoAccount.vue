<!-- //// Neoffice: new file — shown when the user has no JMAP (mail) account.
     The Suite calendar is served by the mail/JMAP backend (Stalwart), so
     without an account there is nothing to render. Instead of a stuck blank
     screen, tell the user what to do. //// -->
<template>
  <div class="flex h-full w-full items-center justify-center p-10">
    <div class="max-w-[460px] flex flex-col items-center gap-4 text-center">
      <LucideCalendarOff class="size-10 text-ink-gray-6" />
      <h2 class="text-lg-semibold text-ink-gray-8">{{ __('No calendar account yet') }}</h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'The calendar needs a mail account to store your events. Ask your administrator to set up your mailbox, then reload this page.'
          )
        }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import LucideCalendarOff from '~icons/lucide/calendar-off'
</script>
