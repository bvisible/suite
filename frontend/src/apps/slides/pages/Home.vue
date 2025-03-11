<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-100 items-center">
		<!-- Navbar -->
		<div
			class="z-10 w-full flex items-center justify-between bg-white p-2 shadow-xl"
			:class="{
				'shadow-gray-300': !previewPresentation,
			}"
		>
			<div class="flex items-center gap-2">
				<img src="../icons/slides.svg" class="h-7" />
				<div class="select-none text-base font-semibold">Slides</div>
			</div>
			<Button variant="solid" label="New" size="sm" @click="dialogAction = 'Create'">
				<template #prefix>
					<FeatherIcon name="plus" class="h-3.5" />
				</template>
			</Button>
		</div>

		<!-- Presentation Cards -->
		<div
			class="w-[80%] h-full my-6 flex flex-col gap-2"
			:class="{
				blur: previewPresentation,
			}"
		>
			<div class="font-semibold text-base text-gray-600 px-4">
				Presentations ({{ presentationList.data?.length }})
			</div>
			<div class="grid grid-cols-5 gap-4 h-auto p-4 overflow-y-auto">
				<div
					v-for="presentation in presentationList.data"
					class="w-[200px] h-[135px] bg-white rounded-lg shadow-xl cursor-pointer"
					:key="presentation.name"
				>
					<div
						class="w-full h-[78%] rounded-t-lg border-b"
						:style="{
							backgroundImage: `url(${presentation.slides[0]?.thumbnail})`,
							backgroundSize: 'cover',
							backgroundPosition: 'center',
						}"
						@click="previewPresentation = presentation"
					></div>
					<div class="w-full h-[22%] flex justify-between px-2 items-center">
						<div class="text-gray-500 text-sm">{{ presentation.title }}</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Presentation Preview -->
		<div
			class="bg-gray-800 fixed top-0 left-0 w-full h-full transition-opacity duration-300 ease-in-out"
			:class="previewPresentation ? 'opacity-30' : 'opacity-0 pointer-events-none'"
			@click="hidePreview()"
		></div>

		<div
			class="z-10 w-[960px] h-[540px] bg-white shadow-2xl rounded-2xl fixed left-[calc(50%-480px)] transition-all duration-300 cursor-pointer hover:scale-[101%]"
			:class="previewPresentation ? 'bottom-[calc(50%-270px)]' : '-bottom-[540px]'"
			:style="previewStyles"
			@mouseenter="showLinkToPresentation = true"
			@mouseleave="showLinkToPresentation = false"
			@click="$router.push(`/${previewPresentation?.name}`)"
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
			class="bg-white text-base w-full h-[380px] fixed transition-all duration-300 flex justify-center"
			:class="previewPresentation ? 'bottom-0' : '-bottom-96'"
		>
			<div
				class="w-[960px] absolute top-[72%] flex flex-col gap-2 px-2"
				v-if="previewPresentation"
			>
				<div
					v-for="(row, index) in previewDetails"
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
				v-if="previewPresentation"
			>
				<Tooltip text="Present" :hover-delay="0.3" placement="right">
					<div
						class="rounded p-2 mx-2 cursor-pointer bg-gray-900"
						@click="enablePresentMode"
					>
						<Presentation size="16" class="text-white stroke-[1.5]" />
					</div>
				</Tooltip>
				<Tooltip
					v-for="action in ['Duplicate', 'Rename', 'Delete']"
					:key="action"
					:text="action"
					:hover-delay="0.3"
					placement="right"
				>
					<div
						class="rounded p-2 mx-2 cursor-pointer bg-gray-200"
						@click="dialogAction = action"
					>
						<component
							:is="
								action == 'Duplicate' ? Copy : action == 'Rename' ? PenLine : Trash
							"
							size="16"
							:strokeWidth="1.5"
						/>
					</div>
				</Tooltip>
			</div>
		</div>
	</div>
	<PresentationActionDialog
		:dialogAction="dialogAction"
		:previewPresentation="previewPresentation"
	/>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

import { Tooltip } from 'frappe-ui'

import { Presentation, Copy, PenLine, Trash } from 'lucide-vue-next'
import PresentationActionDialog from '@/components/PresentationActionDialog.vue'

import { presentationList } from '@/stores/presentation'
import { guessTextColorFromBackground } from '@/utils/color'

import tinycolor from 'tinycolor2'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)
const router = useRouter()

let interval = null
const previewPresentation = ref(null)
const previewSlide = ref(0)
const showLinkToPresentation = ref(false)

const showDialog = ref(false)
const dialogAction = ref('')

const previewStyles = computed(() => ({
	backgroundImage: `url(${previewPresentation.value?.slides[previewSlide.value]?.thumbnail})`,
	backgroundSize: 'cover',
	backgroundPosition: 'center',
}))

const previewDetails = computed(() => {
	if (!previewPresentation.value) return {}

	const { title, slides, creation, modified } = previewPresentation.value
	return [
		{
			Title: title,
			Modified: dayjs(modified).fromNow(),
		},
		{
			'Total Slides': slides.length,
			Created: dayjs(creation).fromNow(),
		},
	]
})

const iconColor = computed(() => {
	const background = tinycolor(
		previewPresentation.value?.slides[previewSlide.value]?.background || 'white',
	).toRgbString()
	return guessTextColorFromBackground(background)
})

const initPreview = () => {
	interval = setInterval(() => {
		previewSlide.value = (previewSlide.value + 1) % previewPresentation.value.slides.length
	}, 2000)
}

const resetPreview = () => {
	previewSlide.value = 0
	clearInterval(interval)
	interval = null
}

const hidePreview = () => {
	previewPresentation.value = null
	resetPreview()
}

const enablePresentMode = async () => {
	await router.replace({
		name: 'Presentation',
		params: { presentationId: previewPresentation.value.name },
		query: { present: true },
	})
}

watch(
	() => previewPresentation.value,
	(val) => {
		val ? initPreview() : resetPreview()
	},
)

onBeforeUnmount(() => {
	resetPreview()
})
</script>
