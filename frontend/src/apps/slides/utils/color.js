export const isBackgroundColorDark = (colorString = '#ffffff') => {
	if (!colorString) colorString = '#ffffff'
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

export const getColorAndOpacity = (colorString = '#000000ff') => {
	if (!colorString?.startsWith('#') || colorString.length !== 9) {
		return {
			color: colorString,
			opacity: 1,
		}
	}

	return {
		color: colorString.slice(0, 7),
		opacity: parseInt(colorString.slice(7, 9), 16) / 255,
	}
}
