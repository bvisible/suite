export const isBackgroundColorDark = (colorString) => {
	const rgb = colorString.replace('#', '')

	const r = parseInt(rgb.slice(0, 2), 16)
	const g = parseInt(rgb.slice(2, 4), 16)
	const b = parseInt(rgb.slice(4, 6), 16)

	const luminance = 0.2989 * r + 0.587 * g + 0.114 * b
	return luminance < 128
}

export const guessTextColorFromBackground = (colorString) => {
	const textColor = isBackgroundColorDark(colorString) ? '#ffffff' : '#000000'
	return textColor
}
