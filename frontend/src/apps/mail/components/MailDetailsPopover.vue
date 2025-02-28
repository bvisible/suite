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
				<template v-if="mail.reply_to">
					<span class="col-span-1 text-gray-500">{{ __('Reply To: ') }}</span>
					<span class="col-span-4 flex flex-col">
						{{ getRecipients(mail.reply_to, true) }}
					</span>
				</template>
				<span class="col-span-1 text-gray-500">{{ __('To: ') }}</span>
				<span class="col-span-4 flex flex-col">
					{{ getRecipients(mail.to, true) }}
				</span>
				<template v-if="mail.cc.length">
					<span class="col-span-1 text-gray-500">{{ __('Cc: ') }}</span>
					<span class="col-span-4 flex flex-col">
						{{ getRecipients(mail.cc, true) }}
					</span>
				</template>
				<template v-if="mail.bcc.length">
					<span class="col-span-1 text-gray-500">{{ __('Bcc: ') }}</span>
					<span class="col-span-4 flex flex-col">
						{{ getRecipients(mail.bcc, true) }}
					</span>
				</template>
				<span class="col-span-1 text-gray-500">{{ __('Date:') }}</span>
				<span class="col-span-4">
					{{ dayjs(mail.creation).format('MMM D, YYYY, h:mm A') }}
				</span>
				<template v-if="mail.subject">
					<span class="col-span-1 text-gray-500">{{ __('Subject:') }}</span>
					<span class="col-span-4">{{ mail.subject }}</span>
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

defineProps<{ mail: object }>()
</script>
