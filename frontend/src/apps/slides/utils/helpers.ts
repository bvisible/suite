import { toast } from 'frappe-ui'
import { getAttachmentUrl } from './mediaUploads'

let isClicked = false
let delay = 200
let clickTimeout: ReturnType<typeof setTimeout> | null = null

const handleSingleAndDoubleClick = (
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

const debounce = (fn: Function, wait = 300) => {
	let timer: ReturnType<typeof setTimeout>
	return function (this: any, ...args: any[]) {
		clearTimeout(timer)
		timer = setTimeout(() => fn.apply(this, args), wait)
	}
}

const generateUniqueId = () => {
	return Math.random().toString(36).slice(2, 11)
}

const setCursorPositionAtEnd = (e: Event) => {
	const selection = window.getSelection()
	if (!e.target || !selection) return

	const target = e.target as HTMLElement
	const range = document.createRange()

	range.selectNodeContents(target)
	range.collapse(false) // set cursor to end of text

	selection.removeAllRanges()
	selection.addRange(range)
}

const handleScrollBarWheelEvent = (e: WheelEvent) => {
	// allow normal scroll behaviour
	if (!isCmdOrCtrl(e)) return

	// prevent zoom event from triggering
	e.preventDefault()
	e.stopPropagation()
}

const cloneObj = (obj: any) => JSON.parse(JSON.stringify(obj))

const copyToClipboard = async (text: string) => {
	if (navigator.clipboard && window.isSecureContext) {
		await navigator.clipboard.writeText(text)
	} else {
		let input = document.createElement('textarea')
		document.body.appendChild(input)
		input.value = text
		input.select()
		document.execCommand('copy')
		document.body.removeChild(input)
	}

	toast.success('Copied to clipboard')
}

const getThumbnailCardStyles = (thumbnail: string) => {
	const thumbnailUrl = getAttachmentUrl(thumbnail)
	return {
		backgroundImage: `url(${thumbnailUrl})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}

const getDocFromHTML = (html: string) => {
	const parser = new DOMParser()
	return parser.parseFromString(html, 'text/html')
}

const isCmdOrCtrl = (e: KeyboardEvent | MouseEvent) => {
	return e.metaKey || e.ctrlKey
}

export {
	handleSingleAndDoubleClick,
	debounce,
	generateUniqueId,
	setCursorPositionAtEnd,
	handleScrollBarWheelEvent,
	cloneObj,
	copyToClipboard,
	getThumbnailCardStyles,
	getDocFromHTML,
	isCmdOrCtrl
}
