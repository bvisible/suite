let isClicked = false
let delay = 200
let clickTimeout: ReturnType<typeof setTimeout> | null = null

export const handleSingleAndDoubleClick = (
	event: MouseEvent,
	singleClickHandler: Function,
	doubleClickHandler: Function,
	...args: any[]
) => {
	// if user clicked a second time clear timeout and register as double click
	if (isClicked) {
		clickTimeout && clearTimeout(clickTimeout)
		isClicked = false
		doubleClickHandler(event, ...args)
	}
	// if user clicked once set timeout for single click function
	// if user doesn't click again within the delay register as single click
	else {
		isClicked = true
		clickTimeout = setTimeout(function () {
			isClicked = false
			singleClickHandler(event, ...args)
		}, delay)
	}
}
