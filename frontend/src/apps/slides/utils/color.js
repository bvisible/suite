import tinycolor from 'tinycolor2'

const hslToRgb = (hslString) => {
	return tinycolor(hslString).toRgb()
}

export const isBackgroundColorDark = (colorString) => {
	let match = colorString?.match(/^rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d*\.?\d+)\s*)?\)$/)
	const HSLmatch = colorString?.match(
		/^hsla?\(\s*(\d+),\s*(\d+)%\s*,\s*(\d+)%\s*(?:,\s*(\d*\.?\d+)\s*)?\)$/,
	)
	if (HSLmatch) {
		const rgbValue = hslToRgb(colorString)
		match = [null, rgbValue.r, rgbValue.g, rgbValue.b]
	}
	if (!match) return false
	const r = parseInt(match[1], 10)
	const g = parseInt(match[2], 10)
	const b = parseInt(match[3], 10)
	const luminance = 0.2989 * r + 0.587 * g + 0.114 * b
	return luminance < 128
}

export const guessTextColorFromBackground = (colorString) => {
	const textColor = isBackgroundColorDark(colorString) ? 'hsl(0, 0%, 100%)' : 'hsl(0, 0%, 0%)'
	return textColor
}
