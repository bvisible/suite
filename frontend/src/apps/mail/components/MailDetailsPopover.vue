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

const dayjs = inject('$dayjs')

const props = defineProps<{ mail: object }>()

const FIELDS = [
	{
		condition: !!props.mail.reply_to,
		label: __('Reply To: '),
		value: () => getRecipients(props.mail.reply_to, true),
	},
	{
		label: __('To: '),
		value: () => getRecipients(props.mail.to, true),
	},
	{
		condition: !!props.mail.cc.length,
		label: __('Cc: '),
		value: () => getRecipients(props.mail.cc, true),
	},
	{
		condition: !!props.mail.bcc.length,
		label: __('Bcc: '),
		value: () => getRecipients(props.mail.bcc, true),
	},
	{
		label: __('Date: '),
		value: () => dayjs(props.mail.creation).format('MMM D, YYYY, h:mm A'),
	},
	{
		condition: !!props.mail.subject,
		label: __('Subject: '),
		value: () => props.mail.subject,
	},
].filter((field) => field.condition !== false)
</script>
