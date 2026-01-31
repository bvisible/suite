<template>
	<Navbar :primaryButton="primaryButtonProps">
		<template #default>
			<div class="flex w-full justify-center">
				<PresentationHeader :title="presentationDoc?.title" />
			</div>
		</template>
		<template v-if="!inReadonlyMode" #actions>
			<Badge v-if="!isOnline" variant="subtle" theme="orange" size="md">
				<LucideWifiOff class="mr-1 size-3.5 stroke-[1.5]" />
				<span>Offline</span>
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

import { presentationDoc } from '@/stores/presentation'

const isOnline = inject('isOnline', null)
const inReadonlyMode = inject('inReadonlyMode', false)

const emit = defineEmits(['startSlideShow'])

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => emit('startSlideShow'),
}
</script>
