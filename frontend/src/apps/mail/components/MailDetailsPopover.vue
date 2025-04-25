<template>
	<Popover>
		<template #target="{ togglePopover }">
			<ChevronDown class="h-3 w-3 cursor-pointer" @click="togglePopover()" />
		</template>
		<template #body-main>
			<div class="grid max-w-lg grid-cols-5 gap-2 p-3 text-sm">
				<span class="col-span-1 text-gray-500">{{ __('From:') }}</span>
				<span class="col-span-4">
					<span class="font-semibold">
						{{ mail.display_name || mail.from_ || mail.sender }}
					</span>
					<span v-if="mail.display_name">
						{{ ` <${mail.from_ || mail.sender}>` }}
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
		condition: !!mail.reply_to,
		label: __('Reply To: '),
		value: () => mail.reply_to,
	},
	{
		label: __('To: '),
		value: () => getRecipients(mail.to, true),
	},
	{
		condition: !!mail.cc.length,
		label: __('Cc: '),
		value: () => getRecipients(mail.cc, true),
	},
	{
		condition: !!mail.bcc.length,
		label: __('Bcc: '),
		value: () => getRecipients(mail.bcc, true),
	},
	{
		label: __('Date: '),
		value: () => dayjs(mail.creation).format('MMM D, YYYY, h:mm A'),
	},
	{
		condition: !!mail.subject,
		label: __('Subject: '),
		value: () => mail.subject,
	},
].filter((field) => field.condition !== false)
</script>
