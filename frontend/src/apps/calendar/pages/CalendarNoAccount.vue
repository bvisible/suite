<!-- //// Neoffice: new file — shown when the user has no JMAP (mail) account.
     The Suite calendar is served by the mail/JMAP backend (Stalwart), so
     without an account there is nothing to render. Instead of a stuck blank
     screen, tell the user what to do. //// -->
<template>
  <!-- //// Neoffice — the Neoffice menu stays on this page: without it the page was a dead end, with no way
       out but the browser's back button (07.10). There is no calendar to list, so its context is empty. //// -->
  <div class="flex h-screen min-h-0 w-full min-w-0">
    <NeoCockpitBridge :surface-app="surfaceApp" :context-nav="[]" :navigate="(r: string) => router.push(r)" />
    <div class="flex min-h-0 min-w-0 flex-1 items-center justify-center p-10">
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
  </div>
</template>

<script setup lang="ts">
//// Neoffice — the router and the cockpit bridge: this page now mounts the Neoffice menu (see the template).
import { useRouter } from 'vue-router'

import LucideCalendarOff from '~icons/lucide/calendar-off'
import calendarLogo from '@/assets/app-logos/calendar.svg'
import NeoCockpitBridge from '@/shell/NeoCockpitBridge.vue'

const router = useRouter()
//// Neoffice — the same surface the calendar's own menu names (components/NeoCockpitSidebar.vue).
const surfaceApp = { name: 'calendar', title: 'Calendar', logo: calendarLogo }
</script>
