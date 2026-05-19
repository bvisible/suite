import { computed } from 'vue'
import { getColorAndOpacity } from '@/utils/color'

const emptyShadow = {
	hasShadow: false,
	offsetX: 0,
	offsetY: 0,
	stdDeviation: 0,
	color: '#000000',
	opacity: 1,
}

export const useSVGShadow = (element) => {
	return computed(() => {
		if (!element.value) return emptyShadow

		const offsetX = Number(element.value.shadowOffsetX || 0)
		const offsetY = Number(element.value.shadowOffsetY || 0)
		const spread = Number(element.value.shadowSpread || 0)
		const { color, opacity } = getColorAndOpacity(element.value.shadowColor || '#000000ff')

		return {
			hasShadow: offsetX || offsetY || spread,
			offsetX,
			offsetY,
			stdDeviation: spread / 2,
			color,
			opacity,
		}
	})
}
