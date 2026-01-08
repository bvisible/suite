<template>
	<Navbar :primaryButton="primaryButtonProps">
		<template #default>
			<PresentationHeader :title="presentationDoc?.title" />
		</template>
		<template v-if="!readonlyMode" #actions>
			<Badge v-if="!isOnline" variant="subtle" theme="orange" size="md">
				<LucideWifiOff class="mr-1 size-3.5 stroke-[1.5]" />
				<span>Offline &ndash; Saving locally</span>
			</Badge>
			<Badge v-if="syncOfflineChangesStatus" variant="subtle" theme="blue" size="md">
				{{ syncOfflineChangesStatus }}
			</Badge>
			<SharePopover v-if="presentationDoc" />
		</template>
	</Navbar>
</template>

<script setup>
import { inject } from 'vue'
import { Presentation } from 'lucide-vue-next'

import { Badge } from 'frappe-ui'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import SharePopover from '@/components/SharePopover.vue'

import { presentationDoc, readonlyMode, syncOfflineChangesStatus } from '@/stores/presentation'

const isOnline = inject('isOnline', null)

const props = defineProps({
	readonlyMode: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['startSlideShow'])

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => emit('startSlideShow'),
}
</script>
