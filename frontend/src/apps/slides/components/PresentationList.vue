<template>
	<div :class="backgroundClasses">
		<!-- Header -->
		<div class="cursor-default px-32 text-base font-semibold text-gray-700 lg:px-40">
			Presentations <span v-if="presentations?.length">({{ presentations?.length }})</span>
		</div>

		<div class="px-32 py-4 lg:px-40">
			<div
				v-if="presentations?.length"
				class="grid grid-cols-3 gap-8 lg:grid-cols-4 lg:gap-10"
			>
				<div
					v-for="presentation in presentations"
					:key="presentation.name"
					class="flex flex-col gap-2"
				>
					<!-- Presentation Card -->
					<!-- added bg-white temporarily to support for first slides with no generated thumbnail -->
					<div
						class="aspect-[16/9] cursor-pointer rounded-lg bg-white shadow-xl hover:scale-[1.01]"
						:style="getCardStyles(presentation)"
						@click="(e) => setPreviewPresentation(e, presentation)"
					></div>

					<!-- Presentation Title  -->
					<div class="cursor-default truncate px-2 text-gray-700 md:text-sm lg:text-base">
						{{ presentation.title }}
					</div>
				</div>
			</div>
			<div v-else class="text-sm text-gray-600">No presentations created yet.</div>
		</div>
	</div>

	<!-- Overlay while previewing certain presentation -->
	<div class="fixed left-0 top-0 h-dvh w-full bg-black opacity-25" v-show="blur"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	presentations: Object,
	blur: Boolean,
})

const emit = defineEmits(['setPreview'])

const backgroundClasses = computed(() => {
	const baseClasses = 'size-full bg-gray-100 flex flex-col gap-2 py-8 overflow-y-auto'
	if (props.blur) return `${baseClasses} blur-[1px]`
	return baseClasses
})

const getCardStyles = (presentation) => {
	return {
		backgroundImage: `url(${presentation.thumbnail || ''})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}

const setPreviewPresentation = (e, presentation) => {
	e.stopPropagation()
	emit('setPreview', presentation)
}
</script>
