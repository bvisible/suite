<template>
	<Popover>
		<template #target="{ togglePopover }">
			<div
				class="my-2 h-4 w-4 cursor-pointer rounded-sm ring-1 ring-gray-400"
				:style="{ backgroundColor: currentColor }"
				@click="togglePopover"
			></div>
		</template>
		<template #body-main>
			<div class="rounded p-2 shadow-2xl" :style="{ width: '192px', height: '200px' }">
				<div class="flex h-full w-full flex-col">
					<div
						ref="shadeSlider"
						class="h-[150px] cursor-pointer rounded-t"
						:style="shadeStyles"
						@mousedown="handleUpdateShade"
					>
						<div
							class="relative h-3 w-3 rounded border"
							:style="{
								backgroundColor: currentColor,
								left: shadeCursorLeft,
								top: shadeCursorTop,
							}"
						></div>
					</div>
					<div class="flex h-[50px] justify-between gap-3 p-3">
						<div
							class="h-full w-8 rounded-sm ring-[1.5px] ring-gray-200"
							:style="{ backgroundColor: currentColor }"
						></div>
						<div class="flex w-full flex-col gap-4">
							<div
								ref="colorSlider"
								class="h-1/5 rounded"
								:style="colorStyles"
								@mousedown="handleUpdateHue"
							>
								<div
									class="relative h-[0.8rem] w-[0.8rem] rounded border border-gray-700 bg-white"
									:style="{ left: hueCursorLeft, top: '-0.25rem' }"
								></div>
							</div>
							<div
								ref="opacitySlider"
								class="h-1/5 rounded"
								:style="opacityStyles"
								@mousedown="handleUpdateOpacity"
							>
								<div
									class="relative h-[0.8rem] w-[0.8rem] rounded border border-gray-700 bg-white"
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
	}
})

const colorStyles = computed(() => {
	return {
		background: `linear-gradient(to right, rgb(255, 0, 0), rgb(255, 0, 255), rgb(0, 0, 255), rgb(0, 255, 255), rgb(0, 255, 0), rgb(255, 255, 0), rgb(255, 0, 0))`,
	}
})

const opacityStyles = `background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 1))`

const shadeSlider = useTemplateRef('shadeSlider')
const colorSlider = useTemplateRef('colorSlider')

let colorRect = useElementBounding(colorSlider)
let shadeRect = useElementBounding(shadeSlider)

const currentColor = defineModel()
const currentHue = ref('hsl(0, 100%, 50%)')
const hueCursorLeft = ref('calc(0% - 6px)')

const currentOpacity = ref(1)
const opacityCursorLeft = ref('calc(100% - 6px)')

const shadeCursorLeft = ref('calc(0% - 6px)')
const shadeCursorTop = ref('calc(100% - 6px)')

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
	if (x > unref(colorRect.width)) {
		x = unref(colorRect.width)
	}
	if (x < 0) {
		x = 0
	}
	var percent = x / unref(colorRect.width)
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

	if (x > unref(shadeRect.width)) {
		x = unref(shadeRect.width)
	}
	if (x < 0) {
		x = 0
	}
	if (y > unref(shadeRect.height)) {
		y = unref(shadeRect.height)
	}
	if (y < 0) {
		y = 0.1
	}

	var xRatio = (x / unref(shadeRect.width)) * 100
	var yRatio = (y / unref(shadeRect.height)) * 100
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
	if (x > unref(colorRect.width)) {
		x = unref(colorRect.width)
	}
	if (x < 0) {
		x = 0
	}
	var percent = x / unref(colorRect.width)
	currentOpacity.value = percent
	currentColor.value = tinycolor(currentColor.value).setAlpha(percent).toHslString()
	opacityCursorLeft.value = `${x - 6}px`
}

const endUpdateOpacity = (e) => {
	window.removeEventListener('mousemove', updateOpacity)
}
</script>
