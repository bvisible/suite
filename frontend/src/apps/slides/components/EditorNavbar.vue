<template>
	<Navbar
		:primaryButton="primaryButtonProps"
		:showNavbarDropdown="showNavbarDropdown"
		@performDropdownAction="(action) => emit('performDropdownAction', action)"
	>
		<template #default>
			<div class="flex w-full justify-center">
				<PresentationHeader :title="presentationDoc?.title" />
			</div>
		</template>
		<template v-if="!readonlyMode" #actions>
			<Badge v-if="!isOnline" variant="subtle" theme="orange" size="md">
				<LucideWifiOff class="mr-1 size-3.5 stroke-[1.5]" />
				<span>Offline</span>
			</Badge>
			<SharePopover v-if="presentationDoc" />
		</template>
	</Navbar>
</template>

<script setup>
import { computed, inject } from 'vue'
import { Presentation } from 'lucide-vue-next'

import { Badge } from 'frappe-ui'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import SharePopover from '@/components/SharePopover.vue'

import { presentationDoc, readonlyMode } from '@/stores/presentation'
import { useRoute } from 'vue-router'

const isOnline = inject('isOnline', null)

const props = defineProps({
	readonlyMode: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['startSlideShow', 'performDropdownAction'])

const route = useRoute()

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => emit('startSlideShow'),
	hide: route.name === 'EditorNew',
}

const showNavbarDropdown = computed(() => {
	if (route.name === 'EditorNew') return false
	return !props.readonlyMode
})
</script>
