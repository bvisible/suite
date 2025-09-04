<template>
	<Navbar :primaryButton="primaryButtonProps">
		<template #default>
			<PresentationHeader :title="presentationDoc?.title" />
		</template>
		<template v-if="!readonlyMode" #actions>
			<SharePopover v-if="presentationDoc" />
		</template>
	</Navbar>
</template>

<script setup>
import { Presentation } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import SharePopover from '@/components/SharePopover.vue'

import { presentationDoc, readonlyMode } from '@/stores/presentation'
import { readonly } from 'vue'

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
