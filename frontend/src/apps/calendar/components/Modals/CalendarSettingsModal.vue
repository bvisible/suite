<!-- //// Neoffice: new file — per-calendar settings opened from the sidebar gear:
     rename, colour, sharing, CalDAV URL, delete. Upstream exposed none of this
     in the SPA. Wraps the existing update_calendar / share_calendar /
     delete_calendars / get_caldav_url endpoints. //// -->
<template>
	<Dialog v-model="show" :options="{ title: __('Calendar settings'), size: 'xl' }">
		<template #body-content>
			<div v-if="detail.loading" class="text-ink-gray-5 py-8 text-center text-sm">
				{{ __('Loading…') }}
			</div>
			<div v-else class="flex flex-col gap-5">
				<!-- Name -->
				<FormControl :label="__('Name')" v-model="name" />

				<!-- Colour -->
				<div>
					<label class="text-ink-gray-5 mb-2 block text-xs">{{ __('Colour') }}</label>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="sw in SWATCHES"
							:key="sw"
							type="button"
							class="size-7 rounded-full border transition"
							:class="
								color === sw
									? 'ring-2 ring-offset-2 ring-outline-gray-3 border-transparent'
									: 'border-outline-gray-2'
							"
							:style="{ backgroundColor: sw }"
							@click="color = sw"
						/>
					</div>
				</div>

				<!-- Sharing -->
				<div>
					<label class="text-ink-gray-5 mb-2 block text-xs">{{ __('Sharing') }}</label>
					<div
						v-if="!colleagues.length"
						class="text-ink-gray-5 rounded border border-dashed p-4 text-center text-sm"
					>
						{{ __('No colleague is available to share with on this server yet.') }}
					</div>
					<div v-else class="flex max-h-52 flex-col gap-1 overflow-y-auto">
						<div
							v-for="p in colleagues"
							:key="p.id"
							class="hover:bg-surface-gray-2 flex items-center gap-3 rounded p-1.5"
						>
							<Avatar :label="p.name" size="md" />
							<div class="min-w-0 flex-1">
								<div class="text-ink-gray-8 truncate text-sm">{{ p.name }}</div>
							</div>
							<select
								v-model="levels[p.id]"
								class="form-select rounded border-outline-gray-2 text-sm"
							>
								<option v-for="opt in LEVELS" :key="opt.value" :value="opt.value">
									{{ opt.label }}
								</option>
							</select>
						</div>
					</div>
				</div>

				<!-- CalDAV -->
				<div>
					<label class="text-ink-gray-5 mb-2 block text-xs">{{ __('CalDAV address') }}</label>
					<div class="flex items-center gap-2">
						<input
							ref="caldavInput"
							readonly
							:value="caldav.data?.url"
							class="form-input flex-1 truncate rounded border-outline-gray-2 text-xs"
							@focus="(e) => e.target.select()"
						/>
						<Button :label="copied ? __('Copied') : __('Copy')" @click="copyCaldav" />
					</div>
					<p class="text-ink-gray-5 mt-1 text-xs">
						{{ __('Add this address in Apple Calendar / Thunderbird to subscribe.') }}
					</p>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-between">
				<Button
					variant="ghost"
					theme="red"
					:label="__('Delete calendar')"
					:loading="deleteRes.loading"
					@click="remove"
				/>
				<div class="flex gap-2">
					<Button :label="__('Cancel')" @click="show = false" />
					<Button
						variant="solid"
						:label="__('Save')"
						:loading="saving"
						@click="save"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Avatar, Button, Dialog, FormControl, createResource } from 'frappe-ui'

import { raiseToast } from '@/apps/calendar/utils'

const { account, calendar } = defineProps<{ account: string; calendar: any }>()
const emit = defineEmits(['reload'])
const show = defineModel<boolean>({ default: false })

const SWATCHES = [
	'#D68A59', '#2C7A7B', '#3B82C4', '#7C5CBF', '#C2557A', '#4C9A5A', '#B7791F', '#5A6270',
]
const LEVELS = [
	{ value: 'none', label: __('No access') },
	{ value: 'free_busy', label: __('See availability') },
	{ value: 'read', label: __('View events') },
	{ value: 'write', label: __('Edit events') },
]
const RIGHTS: Record<string, Record<string, boolean>> = {
	none: {},
	free_busy: { may_read_free_busy: true },
	read: { may_read_free_busy: true, may_read_items: true },
	write: { may_read_free_busy: true, may_read_items: true, may_write_all: true, may_rsvp: true },
}

const name = ref('')
const color = ref(SWATCHES[0])
const levels = reactive<Record<string, string>>({})
const copied = ref(false)
const caldavInput = ref()

const calId = computed(() => (calendar?.name || '').split('|').pop())

// Full calendar record (all fields needed to re-save via update_calendar).
const detail = createResource({
	url: 'suite.mail.doctype.calendar.calendar.get_calendar',
	makeParams: () => ({ account, id: calId.value }),
	onSuccess: (cal: any) => {
		name.value = cal._name
		color.value = cal.color || SWATCHES[0]
		for (const p of colleagues.value) levels[p.id] = 'none'
		for (const r of cal.share_with || []) {
			if (r.may_write_all) levels[r.principal_id] = 'write'
			else if (r.may_read_items) levels[r.principal_id] = 'read'
			else if (r.may_read_free_busy) levels[r.principal_id] = 'free_busy'
		}
	},
})

const principals = createResource({
	url: 'suite.mail.doctype.calendar.calendar.get_shareable_principals',
	makeParams: () => ({ account }),
})
const colleagues = computed(() => principals.data || [])

const caldav = createResource({
	url: 'suite.mail.doctype.calendar.calendar.get_caldav_url',
	makeParams: () => ({ account, id: calId.value }),
})

// //// Neoffice: immediate — the dialog is mounted (v-if) already open, so a
// plain watch on `show` would miss the initial true and never load the data. ////
watch(
	show,
	async (open) => {
		if (!open) return
		copied.value = false
		await principals.fetch()
		detail.fetch()
		caldav.fetch()
	},
	{ immediate: true },
)

function copyCaldav() {
	const url = caldav.data?.url
	if (!url) return
	navigator.clipboard?.writeText(url)
	copied.value = true
	setTimeout(() => (copied.value = false), 1500)
}

const updateRes = createResource({
	url: 'suite.mail.doctype.calendar.calendar.update_calendar',
})
const shareRes = createResource({
	url: 'suite.mail.doctype.calendar.calendar.share_calendar',
})
const deleteRes = createResource({
	url: 'suite.mail.doctype.calendar.calendar.delete_calendars',
	makeParams: () => ({ account, ids: [calId.value] }),
	onSuccess: () => {
		raiseToast(__('Calendar deleted.'))
		show.value = false
		emit('reload')
	},
	onError: (e: any) => raiseToast(e?.messages?.[0] || __('Could not delete the calendar.'), 'error'),
})

const saving = ref(false)

async function save() {
	if (saving.value) return
	saving.value = true
	try {
		const cal = detail.data
		await updateRes.submit({
			account,
			id: calId.value,
			name: name.value.trim(),
			color: color.value,
			description: cal.description,
			sort_order: cal.sort_order,
			include_in_availability: cal.include_in_availability,
			time_zone: cal.time_zone,
			subscribed: cal.subscribed,
			visible: cal.visible,
			default: cal.default,
		})
		await shareRes.submit({
			account,
			id: calId.value,
			share_with: colleagues.value
				.filter((p) => levels[p.id] && levels[p.id] !== 'none')
				.map((p) => ({ principal_id: p.id, ...RIGHTS[levels[p.id]] })),
		})
		raiseToast(__('Calendar updated.'))
		show.value = false
		emit('reload')
	} catch (e: any) {
		raiseToast(e?.messages?.[0] || __('Could not save the calendar.'), 'error')
	} finally {
		saving.value = false
	}
}

function remove() {
	if (deleteRes.loading) return
	deleteRes.submit()
}
</script>
