<!-- //// Neoffice: new file — share a calendar with colleagues. Upstream had no
     sharing UI at all; this drives the new share_calendar/get_shareable_principals
     endpoints. Each colleague gets a simple access level mapped to JMAP rights. //// -->
<template>
	<Dialog v-model="show" :options="{ title: __('Share a calendar') }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<FormControl
					type="select"
					:label="__('Calendar')"
					v-model="calendarId"
					:options="calendarOptions"
				/>

				<div v-if="principals.loading" class="text-ink-gray-5 py-6 text-center text-sm">
					{{ __('Loading colleagues…') }}
				</div>

				<div
					v-else-if="!colleagues.length"
					class="text-ink-gray-5 rounded border border-dashed p-6 text-center text-sm"
				>
					{{ __('No colleague is available to share with on this server yet.') }}
				</div>

				<div v-else class="flex max-h-80 flex-col gap-1 overflow-y-auto">
					<div
						v-for="p in colleagues"
						:key="p.id"
						class="hover:bg-surface-gray-2 flex items-center gap-3 rounded p-1.5"
					>
						<Avatar :label="p.name" size="lg" />
						<div class="min-w-0 flex-1">
							<div class="text-ink-gray-8 truncate text-base">{{ p.name }}</div>
							<div class="text-ink-gray-5 truncate text-xs">{{ p.email }}</div>
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
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" @click="show = false" />
				<Button
					variant="solid"
					:label="__('Save')"
					:loading="saveShare.loading"
					:disabled="!colleagues.length"
					@click="save"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Avatar, Button, Dialog, FormControl, createResource } from 'frappe-ui'

import { raiseToast } from '@/apps/calendar/utils'

const { account, calendars } = defineProps<{ account: string; calendars: any[] }>()
const show = defineModel<boolean>({ default: false })

// Access levels mapped to the JMAP calendar rights.
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

const calendarId = ref('')
const levels = reactive<Record<string, string>>({})

const calendarOptions = computed(() =>
	(calendars || []).map((c) => ({ label: c._name, value: c.name })),
)

const principals = createResource({
	url: 'suite.mail.doctype.calendar.calendar.get_shareable_principals',
	makeParams: () => ({ account }),
})

const colleagues = computed(() => principals.data || [])

// Current sharing of the selected calendar, to pre-fill the levels.
const calendarDetail = createResource({
	url: 'suite.mail.doctype.calendar.calendar.get_calendar',
	makeParams: () => ({ account, id: (calendarId.value || '').split('|').pop() }),
	onSuccess: (cal: any) => {
		for (const p of colleagues.value) levels[p.id] = 'none'
		for (const r of cal?.share_with || []) {
			if (r.may_write_all) levels[r.principal_id] = 'write'
			else if (r.may_read_items) levels[r.principal_id] = 'read'
			else if (r.may_read_free_busy) levels[r.principal_id] = 'free_busy'
		}
	},
})

watch(show, (open) => {
	if (!open) return
	calendarId.value = calendars?.[0]?.name || ''
	principals.fetch()
})

watch([calendarId, colleagues], () => {
	if (calendarId.value && colleagues.value.length) calendarDetail.fetch()
})

const saveShare = createResource({
	url: 'suite.mail.doctype.calendar.calendar.share_calendar',
	makeParams: () => ({
		account,
		id: (calendarId.value || '').split('|').pop(),
		share_with: colleagues.value
			.filter((p) => levels[p.id] && levels[p.id] !== 'none')
			.map((p) => ({ principal_id: p.id, ...RIGHTS[levels[p.id]] })),
	}),
	onSuccess: () => {
		raiseToast(__('Sharing updated.'))
		show.value = false
	},
	onError: (e: any) => raiseToast(e?.messages?.[0] || __('Could not update sharing.'), 'error'),
})

function save() {
	if (saveShare.loading) return
	saveShare.submit()
}
</script>
