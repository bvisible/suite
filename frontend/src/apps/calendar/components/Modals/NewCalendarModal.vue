<!-- //// Neoffice: new file — create a calendar from the SPA. Upstream had no
     UI for this (add_calendar existed backend-only), so users couldn't make a
     "Vacances" calendar. Name + colour, wired to the existing add_calendar. //// -->
<template>
	<Dialog v-model="show" :options="{ title: __('New calendar') }">
		<template #body-content>
			<div class="flex flex-col gap-4">
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
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" @click="show = false" />
				<Button
					variant="solid"
					:label="__('Create')"
					:loading="createCalendar.loading"
					:disabled="!name.trim()"
					@click="create"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Button, Dialog, FormControl, createResource } from 'frappe-ui'

import { raiseToast } from '@/apps/calendar/utils'

const { account } = defineProps<{ account: string }>()
const emit = defineEmits(['created'])
const show = defineModel<boolean>({ default: false })

// A calm, warm-leaning palette (paper/clay-friendly), one saturated per hue.
const SWATCHES = [
	'#D68A59', // clay (brand accent)
	'#2C7A7B',
	'#3B82C4',
	'#7C5CBF',
	'#C2557A',
	'#4C9A5A',
	'#B7791F',
	'#5A6270',
]

const name = ref('')
const color = ref(SWATCHES[0])
const nameInput = ref()

watch(show, (open) => {
	if (open) {
		name.value = ''
		color.value = SWATCHES[0]
		nextTick(() => nameInput.value?.$el?.querySelector('input')?.focus())
	}
})

const createCalendar = createResource({
	url: 'suite.mail.doctype.calendar.calendar.add_calendar',
	makeParams: () => ({ account, name: name.value.trim(), color: color.value }),
	onSuccess: () => {
		raiseToast(__('Calendar “{0}” created.', [name.value.trim()]))
		show.value = false
		emit('created')
	},
	onError: (e: any) => raiseToast(e?.messages?.[0] || __('Could not create the calendar.'), 'error'),
})

function create() {
	if (!name.value.trim() || createCalendar.loading) return
	createCalendar.submit()
}
</script>
