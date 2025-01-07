export const guessTextColorFromBackground = (rgbString) => {
	const match = rgbString?.match(/^rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d*\.?\d+)\s*)?\)$/)
	if (!match) return 'hsl(0, 0%, 0%)'
	const r = parseInt(match[1], 10)
	const g = parseInt(match[2], 10)
	const b = parseInt(match[3], 10)
	const luminance = 0.2989 * r + 0.587 * g + 0.114 * b
	return luminance > 128 ? 'hsl(0, 0%, 0%)' : 'hsl(0, 0%, 100%)'
}
