<template>
	<Popover @open="handlePopoverOpen">
		<template #target="{ togglePopover }">
			<div
				class="my-2 h-4 w-4 cursor-pointer rounded-sm ring-1 ring-gray-400"
				:style="{ backgroundColor: currentColor }"
				@click="togglePopover"
			></div>
		</template>
		<template #body-main>
			<div class="rounded p-3">
				<div class="flex flex-col gap-3">
					<div
						ref="shadeSlider"
						class="cursor-pointer rounded-t"
						:style="shadeStyles"
						@mousedown="handleUpdateShade"
					>
						<div class="relative h-3 w-3 rounded border" :style="shadeRectStyles"></div>
					</div>
					<div class="flex h-8 justify-between p-1">
						<div
							class="h-full w-6 rounded-sm ring-[1.5px] ring-gray-200"
							:style="{ backgroundColor: currentColor }"
						></div>
						<div class="flex flex-col justify-between">
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

const shadeSlider = useTemplateRef('shadeSlider')
const colorSlider = useTemplateRef('colorSlider')

let colorRect = useElementBounding(colorSlider)
let shadeRect = useElementBounding(shadeSlider)

const SLIDER_WIDTH = 125
const SHADE_RECT_WIDTH = 170
const SHADE_RECT_HEIGHT = 130

const sliderClasses = 'h-1/5 rounded cursor-pointer'
const sliderCursorClasses = 'relative h-[0.8rem] w-[0.8rem] rounded border border-gray-700 bg-white'

const currentColor = defineModel()
const currentHue = ref('')
const hueCursorLeft = ref('')

const currentOpacity = ref()
const opacityCursorLeft = ref('')

const shadeCursorLeft = ref('')
const shadeCursorTop = ref('')

let hue = 0
let saturation = 1
let lightness = 1

const handleUpdateHue = (e) => {
	updateHue(e)
	window.addEventListener('mousemove', updateHue)
	window.addEventListener('mouseup', endUpdateHue)
}

const updateHue = (e) => {
	e.preventDefault()
	var x = e.pageX - unref(colorRect.left)
	if (x > SLIDER_WIDTH) {
		x = SLIDER_WIDTH
	}
	if (x < 0) {
		x = 0
	}
	var percent = x / SLIDER_WIDTH
	hue = 360 - 360 * percent
	hueCursorLeft.value = `${x - 6}px`
	var color = tinycolor('hsl ' + hue + ' ' + saturation + ' ' + lightness)
	color = color.toHslString()
	currentHue.value = tinycolor('hsl ' + hue + ' 1 .5').toHslString()
	currentColor.value = color
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

	var x = e.pageX - unref(shadeRect.left)
	var y = e.pageY - unref(shadeRect.top)

	if (x > SHADE_RECT_WIDTH) {
		x = SHADE_RECT_WIDTH
	}
	if (x < 0) {
		x = 0
	}
	if (y > unref(SHADE_RECT_HEIGHT)) {
		y = unref(SHADE_RECT_HEIGHT)
	}
	if (y < 0) {
		y = 0.1
	}

	var xRatio = (x / SHADE_RECT_WIDTH) * 100
	var yRatio = (y / unref(SHADE_RECT_HEIGHT)) * 100
	var hsvValue = 1 - yRatio / 100
	var hsvSaturation = xRatio / 100
	lightness = (hsvValue / 2) * (2 - hsvSaturation)
	saturation = (hsvValue * hsvSaturation) / (1 - Math.abs(2 * lightness - 1))

	shadeCursorLeft.value = `${x - 6}px`
	shadeCursorTop.value = `${y - 6}px`

	var color = tinycolor('hsl ' + hue + ' ' + saturation + ' ' + lightness)
	color = color.toHslString()
	currentColor.value = color
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
	var x = e.pageX - unref(colorRect.left)
	if (x > SLIDER_WIDTH) {
		x = SLIDER_WIDTH
	}
	if (x < 0) {
		x = 0
	}
	var percent = x / SLIDER_WIDTH
	currentOpacity.value = percent
	currentColor.value = tinycolor(currentColor.value).setAlpha(percent).toHslString()
	opacityCursorLeft.value = `${x - 6}px`
}

const endUpdateOpacity = (e) => {
	window.removeEventListener('mousemove', updateOpacity)
}

const handlePopoverOpen = () => {
	const initialHsl = tinycolor(currentColor.value).toHsl()

	hue = initialHsl.h
	saturation = initialHsl.s
	lightness = initialHsl.l

	currentOpacity.value = initialHsl.a
	opacityCursorLeft.value = `${currentOpacity.value * SLIDER_WIDTH - 6}px`

	currentHue.value = tinycolor('hsl ' + hue + ' 1 .5').toHslString()
	hueCursorLeft.value = `${SLIDER_WIDTH - (hue / 360) * SLIDER_WIDTH - 6}px`

	shadeCursorLeft.value = `${saturation * SHADE_RECT_WIDTH - 6}px`
	shadeCursorTop.value = `${(100 - lightness * 100) * (SHADE_RECT_HEIGHT / 100) - 6}px`
}
</script>
