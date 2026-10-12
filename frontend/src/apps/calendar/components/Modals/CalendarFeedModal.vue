<!-- //// Neoffice — added file (no upstream equivalent): share the person's agenda as a private iCal address that
     Google, Outlook and Apple subscribe to (maintenance#1428, suite/calendar/feed.py). It publishes what the person
     sees on this page, read-only. The address is a secret: it can be shown again, replaced (the old one stops
     working) or closed. //// -->
<template>
	<Dialog v-model="show" :title="__('Share your agenda')">
		<template #default>
			<div class="flex flex-col gap-4">
				<p class="text-ink-gray-6 text-sm leading-relaxed">
					{{
						__(
							'Show this agenda in Google Calendar, Outlook or Apple Calendar. They get what you see here, your events and the dates of Neoffice you show, and only show it: what you change there does not come back.',
						)
					}}
				</p>

				<template v-if="state.enabled">
					<div>
						<label class="text-ink-gray-5 mb-1.5 block text-xs">{{ __('Your private address') }}</label>
						<div class="flex items-center gap-2">
							<input
								ref="addressInput"
								class="border-outline-gray-2 bg-surface-gray-1 text-ink-gray-8 min-w-0 flex-1 rounded border px-2 py-1.5 text-xs"
								readonly
								:value="state.url"
								@focus="($event.target as HTMLInputElement).select()"
							/>
							<Button :label="__('Copy')" @click="copy" />
						</div>
					</div>
					<ul class="text-ink-gray-6 list-disc space-y-1 pl-4 text-xs leading-relaxed">
						<li>{{ __('Google Calendar: Other calendars, From URL.') }}</li>
						<li>{{ __('Outlook: Add calendar, Subscribe from web.') }}</li>
						<li>{{ __('Apple Calendar: File, New Calendar Subscription.') }}</li>
					</ul>
					<p class="text-ink-gray-5 text-xs leading-relaxed">
						{{
							__(
								'Google updates a subscribed calendar every few hours, sometimes only once a day; Outlook and Apple within the hour. Keep this address to yourself: whoever has it can read your agenda.',
							)
						}}
					</p>
				</template>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<template v-if="state.enabled">
					<Button
						variant="subtle"
						:theme="confirming ? 'red' : 'gray'"
						:label="confirming ? __('The current address stops working. Click again to confirm.') : __('New address')"
						:loading="busy"
						@click="renew"
					/>
					<Button :label="__('Stop sharing')" :loading="busy" @click="stop.submit()" />
				</template>
				<Button v-else variant="solid" :label="__('Create a private address')" :loading="busy" @click="enable.submit()" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

import { raiseToast } from '@/apps/calendar/utils'

const show = defineModel<boolean>({ default: false })

const state = ref<{ enabled: boolean; url: string }>({ enabled: false, url: '' })
const confirming = ref(false)
const addressInput = ref<HTMLInputElement>()

const take = (answer: any) => {
	state.value = { enabled: !!answer?.enabled, url: answer?.url || '' }
	confirming.value = false
}
const failed = (message: string) => (e: any) => raiseToast(e?.messages?.[0] || message, 'error')

const load = createResource({
	url: 'suite.calendar.feed.get_calendar_feed',
	onSuccess: take,
	onError: failed(__('Could not read your sharing.')),
})
const enable = createResource({
	url: 'suite.calendar.feed.enable_calendar_feed',
	onSuccess: take,
	onError: failed(__('Could not create the address.')),
})
const regenerate = createResource({
	url: 'suite.calendar.feed.regenerate_calendar_feed',
	onSuccess: (answer: any) => {
		take(answer)
		raiseToast(__('New address created. The previous one no longer works.'))
	},
	onError: failed(__('Could not create a new address.')),
})
const stop = createResource({
	url: 'suite.calendar.feed.disable_calendar_feed',
	onSuccess: (answer: any) => {
		take(answer)
		raiseToast(__('Sharing stopped.'))
	},
	onError: failed(__('Could not stop sharing.')),
})

const busy = computed(() => load.loading || enable.loading || regenerate.loading || stop.loading)

// A new address replaces the one that was given, wherever it was pasted: asked twice.
function renew() {
	if (!confirming.value) {
		confirming.value = true
		return
	}
	regenerate.submit()
}

async function copy() {
	try {
		await navigator.clipboard.writeText(state.value.url)
		raiseToast(__('Address copied.'))
	} catch {
		addressInput.value?.select()
		raiseToast(__('Select the address and copy it.'), 'error')
	}
}

watch(show, (open) => {
	if (!open) return
	confirming.value = false
	load.fetch()
})
</script>
