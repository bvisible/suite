<template>
	<div
		class="size-full bg-gray-100 flex flex-col gap-2 py-6 overflow-y-auto"
		:class="{
			'blur-[1px]': blur,
		}"
	>
		<!-- Header -->
		<div class="font-semibold text-base cursor-default text-gray-600 lg:px-40 px-32">
			Presentations ({{ presentations?.length }})
		</div>

		<div class="grid grid-cols-3 lg:grid-cols-4 lg:px-40 lg:py-6 px-32 py-4 lg:gap-10 gap-8">
			<div
				v-for="presentation in presentations"
				:key="presentation.name"
				class="flex flex-col gap-2"
			>
				<!-- Presentation Card -->
				<!-- added bg-white temporarily to support for first slides with no generated thumbnail -->
				<div
					class="aspect-[16/9] bg-white rounded-lg shadow-xl cursor-pointer hover:scale-[1.01]"
					:style="getCardStyles(presentation)"
					@click="(e) => setPreviewPresentation(e, presentation)"
				></div>

				<!-- Presentation Title  -->
				<div class="lg:text-base md:text-sm truncate cursor-default text-gray-700 px-2">
					{{ presentation.title }}
				</div>
			</div>
		</div>
	</div>

	<!-- Overlay while previewing certain presentation -->
	<div class="fixed top-0 left-0 w-full h-dvh bg-black opacity-25" v-show="blur"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	presentations: Object,
	blur: Boolean,
})

const emit = defineEmits(['setPreview'])

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
