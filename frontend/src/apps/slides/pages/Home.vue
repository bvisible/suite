<template>
	<div class="fixed flex flex-col h-screen w-screen">
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
			<Button variant="solid" label="New" size="sm" @click="openDialog('Create')">
				<template #prefix>
					<Plus size="14" class="text-white stroke-[1.5]" />
				</template>
			</Button>
		</div>

		<!-- Presentation Cards -->
		<div
			class="w-full h-full bg-gray-100 flex flex-col gap-2 py-6 overflow-y-auto"
			:class="{
				'blur-[1px]': previewPresentation,
			}"
		>
			<div class="font-semibold text-base text-gray-600 lg:px-40 px-32">
				Presentations ({{ presentationList.data?.length }})
			</div>
			<div
				class="grid grid-cols-3 lg:grid-cols-4 lg:px-40 lg:py-6 px-32 py-4 lg:gap-10 gap-8"
			>
				<div
					v-for="presentation in presentationList.data"
					:key="presentation.name"
					class="flex flex-col gap-2"
				>
					<!-- added bg-white temporarily to support for first slides with no generated thumbnail -->
					<div
						class="aspect-[16/9] bg-white rounded-lg shadow-xl cursor-pointer hover:scale-[1.01]"
						:style="{
							backgroundImage: `url(${presentation.slides[0]?.thumbnail})`,
							backgroundSize: 'cover',
							backgroundPosition: 'center',
						}"
						@click.stop="previewPresentation = presentation"
					></div>
					<div class="lg:text-base md:text-sm text-gray-700 px-2">
						{{ presentation.title }}
					</div>
				</div>
			</div>

			<div
				class="fixed top-0 left-0 w-full h-full bg-black opacity-25"
				v-show="previewPresentation"
			></div>
		</div>

		<!-- Presentation Preview -->
		<div
			class="fixed left-0 w-full h-full transition-all duration-300 ease-in-out flex items-center"
			:class="previewPresentation ? 'top-0' : 'top-[100%]'"
			@click="hidePreview()"
		>
			<div
				class="z-20 w-[70%] absolute left-[calc(50%-31%)] flex justify-between"
				@click.stop
			>
				<div class="w-[88%] flex flex-col gap-8">
					<div
						class="aspect-video bg-white cursor-pointer rounded-2xl shadow-2xl"
						:style="previewStyles"
					></div>
					<div class="flex flex-col gap-2 lg:text-base text-sm cursor-default px-2">
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
				</div>
				<div class="w-[8%] flex flex-col gap-3 pt-[30%]">
					<Tooltip
						v-for="action in presentationActions"
						:text="action.label"
						:hover-delay="0.3"
						placement="right"
					>
						<div
							class="w-8 h-8 flex items-center justify-center rounded cursor-pointer"
							:class="action.label === 'Present' ? 'bg-gray-900' : 'bg-gray-200'"
							@click="action.onClick"
						>
							<component
								:is="action.icon"
								size="16"
								class="stroke-[1.5]"
								:class="{
									'text-white': action.label === 'Present',
								}"
							/>
						</div>
					</Tooltip>
				</div>
			</div>

			<div class="z-10 bg-white h-[53%] w-full absolute bottom-0 left-0" @click.stop></div>
		</div>
	</div>

	<PresentationActionDialog
		v-model="showDialog"
		:dialogAction="dialogAction"
		:presentationTitle="previewPresentation?.title || ''"
		@delete="deletePresentation"
		@create="(title) => addPresentation(title)"
		@duplicate="(title) => addPresentation(title, true)"
	/>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { Tooltip, createResource, call } from 'frappe-ui'

import { Presentation, Copy, PenLine, Trash, Pen, Plus } from 'lucide-vue-next'
import PresentationActionDialog from '@/components/PresentationActionDialog.vue'

import { guessTextColorFromBackground } from '@/utils/color'

import tinycolor from 'tinycolor2'
import dayjs from '@/utils/dayjs'

const router = useRouter()

let interval = null
const previewPresentation = ref(null)
const previewSlide = ref(0)

const showDialog = ref(false)
const dialogAction = ref('')

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

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

const navigateToPresentation = async (name, present) => {
	name = name || previewPresentation.value.name
	await router.replace({
		name: 'Presentation',
		params: { presentationId: name },
		query: { present: present },
	})
}

const presentationActions = [
	{
		icon: Presentation,
		label: 'Present',
		onClick: (e) => navigateToPresentation(previewPresentation.value.name, true),
	},
	{
		icon: PenLine,
		label: 'Edit',
		onClick: (e) => navigateToPresentation(previewPresentation.value.name),
	},
	{
		icon: Copy,
		label: 'Duplicate',
		onClick: (e) => openDialog('Duplicate'),
	},
	{
		icon: Trash,
		label: 'Delete',
		onClick: (e) => openDialog('Delete'),
	},
]

const createPresentationDoc = async (title, duplicateFrom) => {
	return await call('slides.slides.doctype.presentation.presentation.create_presentation', {
		title: title,
		duplicate_from: duplicateFrom,
	})
}

const addPresentation = async (title, duplicate) => {
	closeDialog()
	const presentation = await createPresentationDoc(
		title,
		duplicate ? previewPresentation.value.name : null,
	)
	navigateToPresentation(presentation.name)
}

const deletePresentation = async () => {
	closeDialog()
	await call('slides.slides.doctype.presentation.presentation.delete_presentation', {
		name: previewPresentation.value.name,
	})
	await presentationList.reload()
	previewPresentation.value = null
}

const openDialog = (action) => {
	dialogAction.value = action
	showDialog.value = true
}

const closeDialog = () => {
	showDialog.value = false
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
