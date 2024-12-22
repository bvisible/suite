<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-100 items-center">
		<!-- Navbar -->
		<div
			class="z-10 w-full flex items-center justify-between bg-white p-2 shadow-xl"
			:class="{
				'shadow-gray-300': !selectedPresentation,
			}"
		>
			<div class="flex items-center gap-2">
				<img src="../icons/slides.svg" class="h-7" />
				<div class="select-none font-semibold">Slides</div>
			</div>
		</div>

		<!-- Presentation Cards -->
		<div
			class="w-[80%] h-full my-6 flex flex-col gap-4"
			:class="{
				blur: selectedPresentation,
			}"
		>
			<div class="font-semibold text-gray-600 px-4">
				Presentations ({{ presentationList.data?.length }})
			</div>
			<div class="grid grid-cols-5 gap-4 h-[95%] p-4 overflow-y-auto">
				<div
					v-for="presentation in presentationList.data"
					:key="presentation.name"
					:style="{
						backgroundImage: `url(${presentation.slides[0].thumbnail})`,
						backgroundSize: 'cover',
						backgroundPosition: 'center',
					}"
					class="w-[200px] h-[112.5px] rounded-lg shadow-2xl cursor-pointer hover:scale-[1.01] transition ease-in-out"
					@click="selectedPresentation = presentation"
				></div>
			</div>
		</div>

		<!-- Presentation Preview -->
		<div
			class="bg-gray-800 fixed top-0 left-0 w-full h-full transition-opacity duration-300 ease-in-out"
			:class="selectedPresentation ? 'opacity-30' : 'opacity-0 pointer-events-none'"
			@click="selectedPresentation = null"
		></div>

		<div
			v-show="selectedPresentation"
			class="z-10 w-[960px] h-[540px] bg-white rounded-2xl fixed left-[calc(50%-480px)] top-[calc(50%-270px)]"
			:style="previewStyles"
		></div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { createResource } from 'frappe-ui'

const selectedPresentation = ref(null)

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const previewStyles = computed(() => ({
	backgroundImage: `url(${selectedPresentation.value?.slides[0].thumbnail})`,
	backgroundSize: 'cover',
	backgroundPosition: 'center',
}))
</script>
