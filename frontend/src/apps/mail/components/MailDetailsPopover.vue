<template>
	<Popover>
		<template #target="{ togglePopover }">
			<ChevronDown
				class="text-ink-gray-6 hover:bg-surface-gray-2 h-3 w-3 cursor-pointer rounded-sm"
				@click.stop="togglePopover()"
			/>
		</template>
		<template #body-main>
			<div class="grid max-w-lg grid-cols-5 gap-2 p-3 text-sm">
				<span class="text-ink-gray-5 col-span-1">{{ __('From:') }}</span>
				<span class="col-span-4">
					<span class="font-semibold">
						{{ mail.from_name || mail.from_email }}
					</span>
					<span v-if="mail.from_name">
						{{ ` <${mail.from_email}>` }}
					</span>
				</span>
				<template v-for="field in FIELDS" :key="field.label">
					<span class="col-span-1 text-gray-500">{{ field.label }}</span>
					<span class="col-span-4">{{ field.value() }} </span>
				</template>
			</div>
		</template>
	</Popover>
</template>

<script lang="ts" setup>
import { inject } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { Popover } from 'frappe-ui'

import { getRecipients } from '@/utils'

import type { Mail } from '@/types'

const dayjs = inject('$dayjs')

const { mail } = defineProps<{ mail: Mail }>()

const FIELDS = [
	{
		condition: mail.reply_to.length > 0,
		label: __('Reply To: '),
		value: () => mail.reply_to.join(', '),
	},
	{
		label: __('To: '),
		value: () => getRecipients(mail.recipients.To, true),
	},
	{
		condition: !!mail.recipients.Cc?.length,
		label: __('Cc: '),
		value: () => getRecipients(mail.recipients.Cc, true),
	},
	{
		condition: !!mail.recipients.Bcc?.length,
		label: __('Bcc: '),
		value: () => getRecipients(mail.recipients.Bcc, true),
	},
	{
		label: __('Date: '),
		value: () => dayjs(mail.received_at).format('MMM D, YYYY, h:mm A'),
	},
	{
		condition: !!mail.subject,
		label: __('Subject: '),
		value: () => mail.subject,
	},
].filter((field) => field.condition !== false)
</script>
