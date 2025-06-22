<template>
	<Popover @open="handlePopoverOpen">
		<template #target="{ togglePopover }">
			<div
				class="me-0.5 size-4 cursor-pointer rounded-sm ring-[1.5px] ring-gray-300 ring-offset-1"
				:style="{ backgroundColor: currentColor }"
				@click="togglePopover"
			></div>
		</template>
		<template #body>
			<div class="mt-2 rounded-lg border bg-surface-modal p-3 shadow-xl">
				<div class="flex flex-col gap-3">
					<div
						ref="shadeSlider"
						class="cursor-pointer rounded-t shadow-xl"
						:style="shadeStyles"
						@mousedown="handleUpdateShade"
					>
						<div
							class="relative size-3 rounded border shadow-md transition-transform duration-200 ease-in-out hover:scale-[1.2]"
							:style="shadeRectStyles"
						></div>
					</div>
					<div class="flex h-8 justify-between py-1">
						<div
							class="h-full w-6 rounded-sm ring-1 ring-gray-100 ring-offset-1"
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

const colorHue = ref(0)
const colorSaturation = ref()
const colorValue = ref()

const shadeStyles = computed(() => {
	return {
		background: `linear-gradient(transparent, black), linear-gradient(to right, white, ${currentHue.value})`,
		width: `${SHADE_RECT_WIDTH}px`,
		height: `${SHADE_RECT_HEIGHT}px`,
	}
})

const colorSliderStyles = computed(() => {
	return {
		width: `${SLIDER_WIDTH}px`,
		background: `linear-gradient(to right, rgb(255, 0, 0), rgb(255, 0, 255), rgb(0, 0, 255), rgb(0, 255, 255), rgb(0, 255, 0), rgb(255, 255, 0), rgb(255, 0, 0))`,
	}
})

const opacitySliderStyles = `background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 1))`

const shadeRectStyles = computed(() => {
	return {
		backgroundColor: currentColor.value,
		left: shadeCursorLeft.value,
		top: shadeCursorTop.value,
	}
})

const handleUpdateHue = (e) => {
	updateHue(e)
	window.addEventListener('mousemove', updateHue)
	window.addEventListener('mouseup', endUpdateHue)
}

const hueCursorLeft = computed(() => {
	return `${SLIDER_WIDTH - (colorHue.value / 360) * SLIDER_WIDTH - 6}px`
})

const opacityCursorLeft = computed(() => {
	return `${currentOpacity.value * SLIDER_WIDTH - 6}px`
})

const shadeCursorLeft = computed(() => {
	return `${colorSaturation.value * SHADE_RECT_WIDTH - 6}px`
})

const shadeCursorTop = computed(() => {
	return `${(1 - colorValue.value) * SHADE_RECT_HEIGHT - 6}px`
})

const updateHue = (e) => {
	e.preventDefault()
	const clientX = e.clientX - unref(colorRect.left)

	const x = Math.min(Math.max(clientX, 0), SLIDER_WIDTH)
	colorHue.value = 360 - (360 * x) / SLIDER_WIDTH

	// set currentHue with full saturation and 50% lightness
	currentHue.value = tinycolor({ h: colorHue.value, s: 1, l: 0.5 })

	// update currentColor based on exact hue, saturation, and value
	currentColor.value = tinycolor
		.fromRatio({
			h: colorHue.value,
			s: colorSaturation.value * 100,
			v: colorValue.value * 100,
			a: currentOpacity.value,
		})
		.toHex8String()
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

	colorSaturation.value = x / SHADE_RECT_WIDTH
	colorValue.value = 1 - y / SHADE_RECT_HEIGHT

	currentColor.value = tinycolor({
		h: colorHue.value,
		s: colorSaturation.value * 100,
		v: colorValue.value * 100,
		a: currentOpacity.value,
	}).toHex8String()
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
	currentColor.value = tinycolor(currentColor.value).setAlpha(currentOpacity.value).toHex8String()
}

const endUpdateOpacity = (e) => {
	window.removeEventListener('mousemove', updateOpacity)
}

const handlePopoverOpen = () => {
	const initialHsv = tinycolor(currentColor.value).toHsv()

	colorHue.value = initialHsv.h
	colorSaturation.value = initialHsv.s
	colorValue.value = initialHsv.v
	currentOpacity.value = initialHsv.a

	currentHue.value = tinycolor({ h: colorHue.value, s: 1, l: 0.5 })
}
</script>
