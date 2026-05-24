<template>
	<div
		class="pointer-events-none fixed left-[-10000px] top-0 h-[540px] w-[960px] overflow-hidden"
	>
		<div ref="captureNode" class="h-[540px] w-[960px] overflow-hidden">
			<SlidePreview v-if="slide" :slide="slide" :scale="1" />
		</div>
	</div>
</template>

<script setup>
import { nextTick, useTemplateRef } from 'vue'

import SlidePreview from '@/components/SlidePreview.vue'
import { capturePresentationThumbnail } from '@/utils/presentationThumbnailCapture'

defineProps({
	slide: {
		type: Object,
		default: null,
	},
})

const captureNode = useTemplateRef('captureNode')

const capture = async () => {
	await nextTick()
	if (!captureNode.value) {
		throw new Error('Thumbnail capture surface is not available')
	}
	return capturePresentationThumbnail(captureNode.value)
}

defineExpose({ capture })
</script>
