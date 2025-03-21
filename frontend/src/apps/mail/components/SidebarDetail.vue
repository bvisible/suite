<template>
	<div class="space-y-1 p-2.5">
		<div class="flex items-center justify-between">
			<h3 class="mr-1 flex items-center truncate">
				<span v-if="!mail.seen" class="mr-1.5 h-2 w-2 rounded-full bg-blue-500" />
				<span class="truncate font-semibold" :class="{ italic: !mail.subject }">
					{{ mail.subject || __('[No subject]') }}
				</span>
			</h3>
			<MailDate :datetime="mail.creation" :in-list="true" />
		</div>
		<h4 class="snippet line-clamp-1 text-xs">
			{{ mail.display_name ? mail.display_name : mail.sender }}
		</h4>
		<h5
			class="snippet line-clamp-2 h-9 text-xs text-gray-600"
			:class="{ italic: !mail.snippet }"
		>
			{{ mail.snippet || __('— No message body —') }}
		</h5>
		<div class="flex items-center">
			<AttachmentCapsule
				v-for="attachment in mail.attachments.slice(0, 2)"
				:key="attachment.name"
				:file-name="attachment.file_name"
				class="mr-2 max-w-40"
			/>
			<AttachmentCapsule
				v-if="mail.attachments.length > 2"
				:file-name="__('+{0} more', [mail.attachments.length - 2])"
			/>
			<Badge
				v-if="Object.keys(STATUS).includes(badgeField)"
				class="ml-auto"
				:label="badge.label"
				:theme="badge.theme"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

import AttachmentCapsule from '@/components/AttachmentCapsule.vue'
import MailDate from '@/components/MailDate.vue'

const props = defineProps<{ mail: object }>()

interface BadgeType {
	label: string
	theme: 'gray' | 'blue' | 'green' | 'orange' | 'red'
}

const STATUS = {
	Draft: { label: __('Draft'), theme: 'gray' },
	Queued: { label: __('Queued'), theme: 'orange' },
	Blocked: { label: __('Blocked'), theme: 'red' },
	Failed: { label: __('Failed'), theme: 'red' },
	'DSN Report': { label: __('DSN Report'), theme: 'blue' },
	'DMARC Report': { label: __('DMARC Report'), theme: 'blue' },
}

const badgeField = computed(() =>
	props.mail.mail_type === 'Outgoing Mail' ? props.mail.status : props.mail.type,
)

const badge = computed<BadgeType>(() => STATUS[badgeField.value])
</script>

<style>
.snippet {
	display: -webkit-box;
	-webkit-box-orient: vertical;
	text-overflow: ellipsis;
	width: 100%;
	overflow: hidden;
	line-height: 1.5;
}
</style>
