<template>
	<!-- Slide Elements Panel -->
	<div class="fixed right-0 z-20 flex h-[743px] w-fit border-l bg-white">
		<div class="flex flex-col justify-between">
			<div>
				<Tooltip text="Text" hover-delay="1" placement="left">
					<div
						class="cursor-pointer p-4"
						:class="activeTab == 'text' ? 'bg-gray-100' : ''"
						@click="addTextElement"
					>
						<FeatherIcon
							name="type"
							class="h-5"
							:class="
								activeTab == 'text' ? 'stroke-[1.8px] text-black' : 'text-[#636363]'
							"
						/>
					</div>
				</Tooltip>
				<Tooltip text="Image" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="image" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Video" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="film" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Chart" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="pie-chart" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Slide Properties" hover-delay="1" placement="left">
					<div
						class="cursor-pointer p-4"
						:class="activeTab == 'slide' ? 'bg-gray-100' : ''"
					>
						<FeatherIcon
							name="sliders"
							class="h-5"
							:class="
								activeTab == 'slide'
									? 'stroke-[1.8px] text-black'
									: 'text-[#636363]'
							"
						/>
					</div>
				</Tooltip>
			</div>
			<Tooltip text="Notes" hover-delay="1" placement="left">
				<div class="cursor-pointer p-4">
					<StickyNote size="20" strokeWidth="1.5" color="#636363" />
				</div>
			</Tooltip>
		</div>
	</div>

	<!-- Element Properties Panel -->
	<div
		class="z-5 fixed flex h-[743px] w-[226px] flex-col bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
		:class="activeElement ? 'right-13' : '-right-[174px]'"
	>
		<div v-if="activeTab == 'slide'">
			<div class="px-4 pb-4 pt-4 text-2xs uppercase text-gray-600">Slide Properties</div>

			<div class="flex items-center justify-between border-b px-4 pb-3">
				<div class="py-1 text-sm text-gray-800">Background</div>
				<div
					class="h-4 w-4 cursor-pointer rounded-sm border border-gray-700 bg-white shadow-sm"
				></div>
			</div>
		</div>

		<div v-else-if="activeTab == 'text'">
			<div class="flex flex-col gap-3 px-4 py-2">
				<div class="flex items-center justify-between">
					<button
						class="cursor-pointer rounded-sm p-1"
						:class="
							activeElement.styles.fontWeight == 'bold'
								? 'bg-gray-800 text-white'
								: ''
						"
						@click="toggleProperty('fontWeight')"
					>
						<FeatherIcon name="bold" class="h-4" />
					</button>
					<button
						class="cursor-pointer rounded-sm p-1"
						:class="
							activeElement.styles.fontStyle == 'italic'
								? 'bg-gray-800 text-white'
								: ''
						"
						@click="toggleProperty('fontStyle')"
					>
						<FeatherIcon name="italic" class="h-4" />
					</button>
					<button
						class="cursor-pointer rounded-sm p-1"
						:class="
							activeElement.styles.textDecoration?.includes('underline')
								? 'bg-gray-800 text-white'
								: ''
						"
						@click="toggleProperty('textDecoration', 'underline')"
					>
						<FeatherIcon name="underline" class="h-4" />
					</button>
					<button
						class="cursor-pointer rounded-sm p-1"
						:class="
							activeElement.styles.textDecoration?.includes('line-through')
								? 'bg-gray-800 text-white'
								: ''
						"
						@click="toggleProperty('textDecoration', 'line-through')"
					>
						<Strikethrough size="16" strokeWidth="1.5" />
					</button>
					<button
						class="cursor-pointer rounded-sm p-1"
						:class="
							activeElement.styles.textTransform == 'uppercase'
								? 'bg-gray-800 text-white'
								: ''
						"
						@click="toggleProperty('textTransform')"
					>
						<CaseUpper size="20" strokeWidth="1.5" />
					</button>
				</div>

				<div class="flex items-center justify-between">
					<button class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-left" class="h-4.5" />
					</button>
					<button class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-center" class="h-4.5" />
					</button>
					<button class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-right" class="h-4.5" />
					</button>
					<button class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-justify" class="h-4.5" />
					</button>
					<button class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="list" class="h-4.5" />
					</button>
				</div>
			</div>

			<div class="flex flex-col gap-4 border-y px-4 py-4">
				<div class="text-2xs uppercase text-gray-600">Font</div>
				<FormControl
					type="autocomplete"
					:options="textFonts"
					size="sm"
					variant="subtle"
					:modelValue="activeElement.styles.fontFamily"
					@update:modelValue="(font) => (activeElement.styles.fontFamily = font.value)"
				/>

				<div class="flex items-center justify-between">
					<div class="flex h-7 w-3/5 rounded border bg-gray-100">
						<button
							class="flex w-10 cursor-pointer items-center justify-center"
							@click="(e) => changeFontSize(e, 'decrease')"
						>
							<FeatherIcon name="minus" class="h-3" strokeWidth="2" />
						</button>
						<div class="bg-white">
							<input
								type="number"
								class="h-full w-12 border-none p-0 text-center text-xs font-semibold text-gray-800 focus:outline-none focus:ring-0"
								:value="activeElement.styles.fontSize"
								@input="(e) => changeFontSize(e)"
							/>
						</div>
						<button
							class="flex w-10 cursor-pointer items-center justify-center rounded-r"
							@click="(e) => changeFontSize(e, 'increase')"
						>
							<FeatherIcon name="plus" class="h-3" strokeWidth="2" />
						</button>
					</div>
					<div class="h-6 w-6 cursor-pointer rounded border bg-black shadow-sm"></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Tooltip, FormControl } from 'frappe-ui'
import { StickyNote, Strikethrough, CaseUpper } from 'lucide-vue-next'
import { debounce } from '@/utils/debounce'

const activeElement = defineModel('activeElement', {
	type: Object,
	default: null,
})

const activeTab = computed(() => {
	if (!activeElement.value) return 'slide'
	return activeElement.value.type
})

const addTextElement = () => {
	const text = document.createElement('div')
	text.innerText = 'Text'
	text.style.fontFamily = 'Arial'
	text.style.fontSize = '16px'
	text.style.margin = '14px'
	text.style.color = '#000'
	text.style.zIndex = '100'
	text.style.top = '200px'
	text.style.left = '350px'
	text.style.position = 'absolute'
	text.style.width = 'fit-content'
	text.classList.add('textElement')

	document.querySelector('.slide').appendChild(text)
}

const textFonts = [
	'Helvetica',
	'Arial',
	'Arial Black',
	'Comic Sans MS',
	'Courier New',
	'Georgia',
	'Impact',
	'Lucida Console',
	'Lucida Sans Unicode',
	'Palatino Linotype',
	'Tahoma',
	'Times New Roman',
	'Trebuchet MS',
	'Verdana',
]

const styleProps = ['fontSize', 'fontWeight', 'fontFamily', 'fontStyle', 'textDecoration']

const toggleProperty = (property, textDecoration) => {
	let oldStyle = activeElement.value.styles[property]
	let newStyle = ''

	switch (property) {
		case 'fontWeight':
			newStyle = oldStyle == 'bold' ? 'normal' : 'bold'
			break
		case 'fontStyle':
			newStyle = oldStyle == 'italic' ? 'normal' : 'italic'
			break
		case 'textTransform':
			newStyle = oldStyle == 'uppercase' ? 'none' : 'uppercase'
			break
		default:
			newStyle = oldStyle.includes(textDecoration)
				? oldStyle.replace(textDecoration, '').trim()
				: oldStyle + ' ' + textDecoration
	}
	activeElement.value.styles[property] = newStyle
}

const updateFontSize = debounce((e) => {
	activeElement.value.styles.fontSize = parseInt(e.target.value)
}, 500)

const changeFontSize = (e, direction) => {
	if (!direction) updateFontSize(e)
	else if (direction == 'increase') {
		activeElement.value.styles.fontSize += 1
	} else if (direction == 'decrease' && activeElement.value.styles.fontSize > 5) {
		activeElement.value.styles.fontSize -= 1
	}
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
