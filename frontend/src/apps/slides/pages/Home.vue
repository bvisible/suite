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
						backgroundImage: `url(${presentation.slides[0]?.thumbnail})`,
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
			@click="hidePreview()"
		></div>

		<div
			class="z-10 w-[960px] h-[540px] bg-white shadow-2xl rounded-2xl fixed left-[calc(50%-480px)] transition-all duration-300 cursor-pointer hover:scale-[101%]"
			:class="activePresentation ? 'bottom-[calc(50%-270px)]' : '-bottom-[540px]'"
			:style="previewStyles"
			@mouseenter="showLinkToPresentation = true"
			@mouseleave="showLinkToPresentation = false"
			@click="$router.push(`/${activePresentation?.name}`)"
		>
			<FeatherIcon
				v-if="showLinkToPresentation"
				class="h-5 absolute top-4 right-4 opacity-70"
				name="arrow-up-right"
				:style="{
					color: iconColor,
				}"
			/>
		</div>

		<!-- Presentation Details -->
		<div
			class="bg-white w-full h-[380px] fixed transition-all duration-300 flex justify-center"
			:class="activePresentation ? 'bottom-0' : '-bottom-96'"
		>
			<div
				class="w-[960px] absolute top-[72%] flex flex-col gap-2 px-2"
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

			<div
				class="absolute top-[6%] right-[12.5%] flex flex-col gap-3"
				v-if="activePresentation"
			>
				<div class="rounded p-2 mx-2 cursor-pointer bg-gray-900" @click="enablePresentMode">
					<Presentation size="16" :strokeWidth="1.5" class="text-white" />
				</div>
				<div class="rounded p-2 mx-2 cursor-pointer bg-gray-200" @click="showDialog = true">
					<Copy size="16" :strokeWidth="1.5" />
				</div>
			</div>
		</div>
	</div>

	<Dialog class="pb-0" v-model="showDialog" :options="{ size: 'sm' }">
		<template #body>
			<div class="flex flex-col gap-6 p-6">
				<div class="flex items-center justify-between">
					<div class="text-md font-semibold text-gray-900">Duplicate Presentation</div>
					<FeatherIcon name="x" class="h-4 cursor-pointer" @click="showDialog = false" />
				</div>
				<FormControl
					:type="'text'"
					size="md"
					variant="subtle"
					placeholder="Presentation Title"
					v-model="newPresentationTitle"
				/>
				<Button variant="solid" label="Create Copy" @click="createPresentation()">
					<template #prefix>
						<FeatherIcon name="copy" class="h-3.5" />
					</template>
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { createResource, Dialog, FormControl, call } from 'frappe-ui'
import { Presentation, Copy } from 'lucide-vue-next'
import { guessTextColorFromBackground } from '../utils/color'
import tinycolor from 'tinycolor2'

import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { startSlideShow } from '@/stores/slide'

dayjs.extend(relativeTime)
const router = useRouter()

let interval = null
const activePresentation = ref(null)
const previewSlide = ref(0)
const showLinkToPresentation = ref(false)

const showDialog = ref(false)
const newPresentationTitle = ref('')

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const previewStyles = computed(() => ({
	backgroundImage: `url(${activePresentation.value?.slides[previewSlide.value]?.thumbnail})`,
	backgroundSize: 'cover',
	backgroundPosition: 'center',
}))

const activePresentationDetails = computed(() => {
	if (!activePresentation.value) return {}

	const { title, slides, creation, modified } = activePresentation.value
	return [
		{
			Title: title,
			Modified: dayjs(modified).fromNow(),
		},
		{
			Slides: slides.length,
			Created: dayjs(creation).fromNow(),
		},
	]
})

const iconColor = computed(() => {
	const background = tinycolor(
		activePresentation.value?.slides[previewSlide.value]?.background || 'white',
	).toRgbString()
	return guessTextColorFromBackground(background)
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

const hidePreview = () => {
	activePresentation.value = null
	resetPreview()
}

const enablePresentMode = async () => {
	await router.push(`/${activePresentation.value.name}`)
	await startSlideShow()
}

const createPresentation = async () => {
	showDialog.value = false
	const presentation = await call(
		'slides.slides.doctype.presentation.presentation.duplicate_presentation',
		{
			title: newPresentationTitle.value,
			presentation_name: activePresentation.value.name,
		},
	)
	await router.push(`/${presentation.name}`)
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
