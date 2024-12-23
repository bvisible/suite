<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-100 items-center">
		<!-- Navbar -->
		<div
			class="z-10 w-full flex items-center justify-between bg-white p-2 shadow-xl"
			:class="{
				'shadow-gray-300': !activePresentation,
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
				blur: activePresentation,
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
					@click="activePresentation = presentation"
				></div>
			</div>
		</div>

		<!-- Presentation Preview -->
		<div
			class="bg-gray-800 fixed top-0 left-0 w-full h-full transition-opacity duration-300 ease-in-out"
			:class="activePresentation ? 'opacity-30' : 'opacity-0 pointer-events-none'"
			@click="activePresentation = null"
		></div>

		<div
			class="z-10 w-[960px] h-[540px] bg-white shadow-2xl shadow-gray-300 rounded-2xl fixed left-[calc(50%-480px)] transition-all duration-300 cursor-pointer hover:scale-[101%]"
			:class="activePresentation ? 'bottom-[calc(50%-270px)]' : '-bottom-[540px]'"
			:style="previewStyles"
			@mouseenter="showLinkToPresentation = true"
			@mouseleave="showLinkToPresentation = false"
			@click="$router.push(`/${activePresentation?.name}`)"
		>
			<FeatherIcon
				v-if="showLinkToPresentation"
				class="h-5 absolute top-4 right-4 text-white"
				name="arrow-up-right"
			/>
		</div>

		<!-- Presentation Details -->
		<div
			class="bg-white w-full h-[380px] fixed transition-all duration-300 flex justify-center"
			:class="activePresentation ? 'bottom-0' : '-bottom-96'"
		>
			<div
				class="w-[960px] fixed top-[88%] flex flex-col gap-2 px-2"
				v-if="activePresentation"
			>
				<div
					v-for="(row, index) in activePresentationDetails"
					:key="index"
					class="flex items-center justify-between"
				>
					<div
						v-for="(detailValue, detailLabel) in row"
						:key="detailLabel"
						class="flex items-center gap-2"
					>
						<div class="font-semibold text-gray-700">{{ detailLabel }}</div>
						<div class="font-semibold text-gray-600">{{ detailValue }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { createResource } from 'frappe-ui'

let interval = null
const activePresentation = ref(null)
const previewSlide = ref(0)
const showLinkToPresentation = ref(false)

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const previewStyles = computed(() => ({
	backgroundImage: `url(${activePresentation.value?.slides[previewSlide.value].thumbnail})`,
	backgroundSize: 'cover',
	backgroundPosition: 'center',
}))

const activePresentationDetails = computed(() => {
	if (!activePresentation.value) return {}

	const { title, slides, creation, modified } = activePresentation.value
	return [
		{
			Title: title,
			Modified: modified,
		},
		{
			Slides: slides.length,
			Created: creation,
		},
	]
})

const initPreview = () => {
	interval = setInterval(() => {
		previewSlide.value = (previewSlide.value + 1) % activePresentation.value.slides.length
	}, 2000)
}

const resetPreview = () => {
	previewSlide.value = 0
	clearInterval(interval)
	interval = null
}

watch(
	() => activePresentation.value,
	(val) => {
		val ? initPreview() : resetPreview()
	},
)

onBeforeUnmount(() => {
	resetPreview()
})
</script>
