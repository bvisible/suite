<!-- //// Neoffice — frappe-ui's Dialog API changed with the submodule bump
     (bceea1dbe): `:options="{ title, size }"` is gone in favour of plain props,
     and the `#body-content` slot is now the DEFAULT slot. Passing the old shape
     is not an error — Vue just ignores an unknown prop and never renders an
     unknown slot — so the dialog opened EMPTY: no title, no fields, only the
     footer. Found on screen 31.08.2026, the calendar settings modal had lost its
     name, colour, sharing and CalDAV link. Upstream's own
     apps/drive/components/Settings/WebDAVSettings.vue still passes the old shape
     and has the same bug; worth reporting. //// -->
<!-- //// Neoffice: create a calendar from the SPA. Two modes: a plain new Suite
     calendar (name + colour -> add_calendar), OR subscribe an EXTERNAL calendar
     (Google / iCloud / Outlook) by its secret iCal URL -> neoffice_theme
     calendar_connectors.add_external_source (read-only aggregation). //// -->
<template>
	<Dialog v-model="show" :title="__('Add a calendar')">
		<template #default>
			<div class="flex flex-col gap-4">
				<!-- Mode selector -->
				<div class="bg-surface-gray-2 flex rounded-lg p-0.5 text-sm">
					<button
						type="button"
						class="flex-1 rounded-md py-1.5 transition"
						:class="mode === 'new' ? 'bg-surface-white shadow-sm' : 'text-ink-gray-6'"
						@click="mode = 'new'"
					>
						{{ __('New calendar') }}
					</button>
					<button
						type="button"
						class="flex-1 rounded-md py-1.5 transition"
						:class="mode === 'external' ? 'bg-surface-white shadow-sm' : 'text-ink-gray-6'"
						@click="mode = 'external'"
					>
						{{ __('External calendar') }}
					</button>
				</div>

				<!-- Mode: new Suite calendar -->
				<template v-if="mode === 'new'">
					<FormControl
						ref="nameInput"
						:label="__('Name')"
						v-model="name"
						:placeholder="__('e.g. Holidays, Team, Personal')"
						@keydown.enter="create"
					/>
					<div>
						<label class="text-ink-gray-5 mb-2 block text-xs">{{ __('Colour') }}</label>
						<div class="flex flex-wrap gap-2">
							<button
								v-for="swatch in SWATCHES"
								:key="swatch"
								type="button"
								class="size-7 rounded-full border transition"
								:class="
									color === swatch
										? 'ring-2 ring-offset-2 ring-outline-gray-3 border-transparent'
										: 'border-outline-gray-2'
								"
								:style="{ backgroundColor: swatch }"
								@click="color = swatch"
							/>
						</div>
					</div>
				</template>

				<!-- Mode: external (Google / iCloud / Outlook) -->
				<template v-else>
					<FormControl
						type="select"
						:label="__('Provider')"
						v-model="provider"
						:options="['Google', 'iCloud', 'Outlook', 'Other']"
					/>
					<FormControl
						:label="__('Title')"
						v-model="extTitle"
						:placeholder="__('e.g. My Gmail')"
					/>
					<FormControl
						:label="__('Secret iCal (ICS) address')"
						v-model="icsUrl"
						:placeholder="'https://…/basic.ics'"
					/>
					<p class="text-ink-gray-5 text-xs leading-relaxed">
						{{ providerHint }}
					</p>
					<p class="text-ink-gray-4 text-xs">
						{{ __('Read-only: events from this account will appear here, in CalDAV and on mobile.') }}
					</p>
				</template>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" @click="show = false" />
				<Button
					variant="solid"
					:label="__('Add')"
					:loading="busy"
					:disabled="!canCreate"
					@click="create"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Button, Dialog, FormControl, createResource } from 'frappe-ui'

import { raiseToast } from '@/apps/calendar/utils'

const { account } = defineProps<{ account: string }>()
const emit = defineEmits(['created'])
const show = defineModel<boolean>({ default: false })

const SWATCHES = [
	'#D68A59', '#2C7A7B', '#3B82C4', '#7C5CBF', '#C2557A', '#4C9A5A', '#B7791F', '#5A6270',
]

const HINTS: Record<string, string> = {
	Google: __(
		'Google Calendar → Settings → your calendar → "Integrate calendar" → copy the "Secret address in iCal format".',
	),
	iCloud: __(
		'iCloud calendar → Share → Public Calendar → copy the link (change webcal:// to https://).',
	),
	Outlook: __(
		'Outlook → Settings → Calendar → Shared calendars → Publish → copy the ICS link.',
	),
	Other: __('Paste the private iCal (.ics) URL of the calendar you want to aggregate.'),
}

const mode = ref<'new' | 'external'>('new')
const name = ref('')
const color = ref(SWATCHES[0])
const nameInput = ref()

const provider = ref('Google')
const extTitle = ref('')
const icsUrl = ref('')

const providerHint = computed(() => HINTS[provider.value] || HINTS.Other)
const busy = computed(() => createCalendar.loading || addExternal.loading)
const canCreate = computed(() =>
	mode.value === 'new'
		? !!name.value.trim()
		: !!extTitle.value.trim() && /^https?:\/\//.test(icsUrl.value.trim()),
)

watch(show, (open) => {
	if (!open) return
	mode.value = 'new'
	name.value = ''
	color.value = SWATCHES[0]
	provider.value = 'Google'
	extTitle.value = ''
	icsUrl.value = ''
	nextTick(() => nameInput.value?.$el?.querySelector('input')?.focus())
})

const createCalendar = createResource({
	url: 'suite.calendar.doctype.calendar.calendar.add_calendar',
	makeParams: () => ({ account, name: name.value.trim(), color: color.value }),
	onSuccess: () => {
		raiseToast(__('Calendar “{0}” created.', [name.value.trim()]))
		show.value = false
		emit('created')
	},
	onError: (e: any) => raiseToast(e?.messages?.[0] || __('Could not create the calendar.'), 'error'),
})

const addExternal = createResource({
	url: 'neoffice_theme.calendar_connectors.add_external_source',
	makeParams: () => ({
		title: extTitle.value.trim(),
		ics_url: icsUrl.value.trim(),
		provider: provider.value,
		calendar_name: extTitle.value.trim(),
	}),
	onSuccess: (r: any) => {
		raiseToast(__('External calendar added — {0}', [r?.result || __('synced')]))
		show.value = false
		emit('created')
	},
	onError: (e: any) =>
		raiseToast(e?.messages?.[0] || __('Could not add the external calendar.'), 'error'),
})

function create() {
	if (busy.value || !canCreate.value) return
	if (mode.value === 'new') createCalendar.submit()
	else addExternal.submit()
}
</script>
