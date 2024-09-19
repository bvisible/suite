<template>
	<div class="flex flex-col gap-3 px-4 py-2">
		<div class="flex items-center justify-between">
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.fontWeight == 'bold' ? 'bg-gray-800 text-white' : ''"
				@click="toggleProperty('fontWeight')"
			>
				<FeatherIcon name="bold" class="h-4" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.fontStyle == 'italic' ? 'bg-gray-800 text-white' : ''"
				@click="toggleProperty('fontStyle')"
			>
				<FeatherIcon name="italic" class="h-4" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="
					activeElement.textDecoration?.includes('underline')
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
					activeElement.textDecoration?.includes('line-through')
						? 'bg-gray-800 text-white'
						: ''
				"
				@click="toggleProperty('textDecoration', 'line-through')"
			>
				<Strikethrough size="16" strokeWidth="1.5" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textTransform == 'uppercase' ? 'bg-gray-800 text-white' : ''"
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
		<div class="text-2xs uppercase text-gray-600">Transparency</div>
		<div class="flex items-center justify-between">
			<div class="relative my-4 me-6 h-[1.5px] w-full">
				<div id="opacityBar" class="absolute top-0 h-full w-full rounded bg-gray-300"></div>
				<div
					class="absolute top-0 h-full rounded bg-gray-900"
					:style="{ width: activeElement.opacity + '%' }"
				></div>
				<div
					id="opacityHandle"
					class="absolute -top-[5px] h-3 w-3 cursor-pointer rounded-md border bg-gray-900"
					:style="{ left: activeElement.opacity + '%' }"
					@mousedown="handleDragStart"
				></div>
			</div>
			<input
				type="number"
				class="h-7 w-10 rounded border border-gray-400 px-2 py-0 text-center text-sm focus:border-[1.5px] focus:border-gray-500 focus:ring-0"
				v-model="activeElement.opacity"
			/>
		</div>
	</div>

	<div class="flex flex-col gap-4 border-b px-4 py-4">
		<div class="text-2xs uppercase text-gray-600">Font</div>
		<FormControl
			type="autocomplete"
			:options="textFonts"
			size="sm"
			variant="subtle"
			:modelValue="activeElement.fontFamily"
			@update:modelValue="(font) => (activeElement.fontFamily = font.value)"
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
						:value="activeElement.fontSize"
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

	<div class="flex flex-col gap-2 border-b px-4 py-4">
		<div class="text-2xs uppercase text-gray-600">Spacing</div>
		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-700">Line Height</div>
			<FormControl
				class="w-1/3"
				type="number"
				size="sm"
				variant="subtle"
				:modelValue="activeElement.lineHeight"
			/>
		</div>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-700">Letter Spacing</div>
			<FormControl
				class="w-1/3"
				type="number"
				size="sm"
				variant="subtle"
				:modelValue="activeElement.letterSpacing"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, useTemplateRef } from 'vue'
import { FormControl } from 'frappe-ui'
import { StickyNote, Strikethrough, CaseUpper } from 'lucide-vue-next'

import { debounce } from '@/utils/debounce'
import { activeElement } from '@/stores/slide'

const textFonts = [
	'Arial',
	'Arial Black',
	'Comic Sans MS',
	'Courier New',
	'Georgia',
	'Helvetica',
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
	let oldStyle = activeElement.value[property]
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
	activeElement.value[property] = newStyle
}

const updateFontSize = debounce((e) => {
	activeElement.value.fontSize = parseInt(e.target.value)
}, 500)

const changeFontSize = (e, direction) => {
	if (!direction) updateFontSize(e)
	else if (direction == 'increase') {
		activeElement.value.fontSize += 1
	} else if (direction == 'decrease' && activeElement.value.fontSize > 5) {
		activeElement.value.fontSize -= 1
	}
}

const handleDragStart = (e) => {
	e.preventDefault()
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', handleDragEnd)
}

const handleDrag = (e) => {
	e.preventDefault()
	let opacityBar = document.getElementById('opacityBar')

	if (e.clientX < opacityBar.getBoundingClientRect().left) {
		activeElement.value.opacity = 0
		return
	} else if (e.clientX > opacityBar.getBoundingClientRect().right) {
		activeElement.value.opacity = 100
		return
	}

	let currentX = e.clientX
	let opacity = Math.round(
		((currentX - opacityBar.getBoundingClientRect().left) / opacityBar.offsetWidth) * 100,
	)
	opacity = Math.min(Math.max(opacity, 0), 100)
	activeElement.value.opacity = opacity
}

const handleDragEnd = (e) => {
	e.preventDefault()
	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', handleDragEnd)
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
