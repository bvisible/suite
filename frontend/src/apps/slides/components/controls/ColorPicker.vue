<template>
	<Popover @open="handlePopoverOpen">
		<template #target="{ togglePopover }">
			<div
				class="me-0.5 h-4 w-4 cursor-pointer rounded-sm ring-[1.5px] ring-offset-1 ring-gray-300"
				:style="{ backgroundColor: currentColor }"
				@click="togglePopover"
			></div>
		</template>
		<template #body>
			<div class="rounded-lg border bg-surface-modal shadow-xl p-3 mt-2">
				<div class="flex flex-col gap-3">
					<div
						ref="shadeSlider"
						class="cursor-pointer rounded-t shadow-xl"
						:style="shadeStyles"
						@mousedown="handleUpdateShade"
					>
						<div
							class="relative size-3 rounded border shadow-md hover:scale-[1.2] transition-transform duration-200 ease-in-out"
							:style="shadeRectStyles"
						></div>
					</div>
					<div class="flex h-8 justify-between py-1">
						<div
							class="h-full w-6 rounded-sm ring-1 ring-offset-1 ring-gray-100"
							:style="{ backgroundColor: currentColor }"
						></div>
						<div class="flex flex-col justify-between px-1">
							<div
								ref="colorSlider"
								:class="sliderClasses"
								:style="colorSliderStyles"
								@mousedown="handleUpdateHue"
							>
								<div
									:class="sliderCursorClasses"
									:style="{ left: hueCursorLeft, top: '-0.25rem' }"
								></div>
							</div>
							<div
								ref="opacitySlider"
								:class="sliderClasses"
								:style="opacitySliderStyles"
								@mousedown="handleUpdateOpacity"
							>
								<div
									:class="sliderCursorClasses"
									:style="{ left: opacityCursorLeft, top: '-0.25rem' }"
								></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { ref, unref, computed, useTemplateRef } from 'vue'
import { useElementBounding } from '@vueuse/core'

import { Popover } from 'frappe-ui'

import tinycolor from 'tinycolor2'

const shadeSlider = useTemplateRef('shadeSlider')
const colorSlider = useTemplateRef('colorSlider')

let colorRect = useElementBounding(colorSlider)
let shadeRect = useElementBounding(shadeSlider)

const SLIDER_WIDTH = 125
const SHADE_RECT_WIDTH = 170
const SHADE_RECT_HEIGHT = 130

const sliderClasses = 'h-1/5 rounded cursor-pointer'
const sliderCursorClasses =
	'relative size-[0.8rem] rounded shadow border border-gray-200 bg-white hover:scale-[1.1] transition-transform duration-200 ease-in-out'

const currentColor = defineModel()

const currentHue = ref()
const currentOpacity = ref()

const hue = ref(0)
const saturation = ref()
const lightness = ref()

const shadeStyles = computed(() => {
	return {
		background: `linear-gradient(transparent, black), linear-gradient(to right, white, ${currentHue.value})`,
		width: '170px',
		height: '130px',
	}
})

const colorSliderStyles = computed(() => {
	return {
		width: `${SLIDER_WIDTH}px`,
		background: `linear-gradient(to right, rgb(255, 0, 0), rgb(255, 0, 255), rgb(0, 0, 255), rgb(0, 255, 255), rgb(0, 255, 0), rgb(255, 255, 0), rgb(255, 0, 0))`,
	}
})

const opacitySliderStyles = `background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 1))`

const shadeRectStyles = computed(() => ({
	backgroundColor: currentColor.value,
	left: shadeCursorLeft.value,
	top: shadeCursorTop.value,
}))

const handleUpdateHue = (e) => {
	updateHue(e)
	window.addEventListener('mousemove', updateHue)
	window.addEventListener('mouseup', endUpdateHue)
}

const hueCursorLeft = computed(() => {
	return `${SLIDER_WIDTH - (hue.value / 360) * SLIDER_WIDTH - 6}px`
})

const opacityCursorLeft = computed(() => {
	return `${currentOpacity.value * SLIDER_WIDTH - 6}px`
})

const shadeCursorLeft = computed(() => {
	return `${saturation.value * SHADE_RECT_WIDTH - 6}px`
})

const shadeCursorTop = computed(() => {
	return `${(1 - lightness.value) * SHADE_RECT_HEIGHT - 6}px`
})

const updateHue = (e) => {
	e.preventDefault()
	const clientX = e.clientX - unref(colorRect.left)

	const x = Math.min(Math.max(clientX, 0), SLIDER_WIDTH)
	hue.value = 360 - (360 * x) / SLIDER_WIDTH

	// set currentHue with full saturation and 50% lightness
	currentHue.value = tinycolor('hsl ' + hue.value + ' 1 .5').toHslString()

	// update currentColor based on exact hue, saturation, and lightness
	currentColor.value = tinycolor
		.fromRatio({
			h: hue.value,
			s: saturation.value * 100,
			v: lightness.value * 100,
			a: currentOpacity.value,
		})
		.toHslString()
}

const endUpdateHue = (e) => {
	window.removeEventListener('mousemove', updateHue)
}

const handleUpdateShade = (e) => {
	updateShade(e)
	window.addEventListener('mousemove', updateShade)
	window.addEventListener('mouseup', endUpdateShade)
}

const updateShade = (e) => {
	e.preventDefault()

	const clientX = e.clientX - unref(shadeRect.left)
	const clientY = e.clientY - unref(shadeRect.top)

	const x = Math.min(Math.max(clientX, 0), SHADE_RECT_WIDTH)
	const y = Math.min(Math.max(clientY, 0), SHADE_RECT_HEIGHT)

	lightness.value = 1 - y / SHADE_RECT_HEIGHT
	saturation.value = x / SHADE_RECT_WIDTH

	currentColor.value = tinycolor
		.fromRatio({
			h: hue.value,
			s: saturation.value * 100,
			v: lightness.value * 100,
			a: currentOpacity.value,
		})
		.toHslString()
}

const endUpdateShade = (e) => {
	window.removeEventListener('mousemove', updateShade)
}

const handleUpdateOpacity = (e) => {
	updateOpacity(e)
	window.addEventListener('mousemove', updateOpacity)
	window.addEventListener('mouseup', endUpdateOpacity)
}

const updateOpacity = (e) => {
	e.preventDefault()

	const clientX = e.clientX - unref(colorRect.left)

	const x = Math.min(Math.max(clientX, 0), SLIDER_WIDTH)

	currentOpacity.value = x / SLIDER_WIDTH
	currentColor.value = tinycolor(currentColor.value).setAlpha(currentOpacity.value).toHslString()
}

const endUpdateOpacity = (e) => {
	window.removeEventListener('mousemove', updateOpacity)
}

const handlePopoverOpen = () => {
	const initialHsl = tinycolor(currentColor.value).toHsl()

	hue.value = initialHsl.h
	saturation.value = initialHsl.s
	lightness.value = initialHsl.l

	currentOpacity.value = initialHsl.a
	currentHue.value = tinycolor('hsl ' + hue.value + ' 1 .5').toHslString()
}
</script>
