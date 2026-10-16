//// Neoffice — added file (no upstream equivalent): the search field of Drive's toolbar, found again when its component
//// no longer exposes `el` (maintenance#1623). Escape threw "Cannot read properties of undefined (reading 'blur')" on every
//// press and never cleared the search.

type FieldRef =
	| { inputElement?: HTMLElement | null; el?: HTMLElement | null; $el?: Node | null }
	| null
	| undefined

/**
 * The text input behind a frappe-ui TextInput ref: the `inputElement` it exposes now, the `el` it exposed before, else the
 * input inside its root (a component with several root nodes has a text node there, which holds none).
 */
export function inputOf(field: FieldRef): HTMLInputElement | null {
	const exposed = field?.inputElement ?? field?.el
	if (exposed) return exposed as HTMLInputElement
	const root = field?.$el as HTMLElement | null | undefined
	if (!root) return null
	if (root.tagName === 'INPUT') return root as HTMLInputElement
	return root.querySelector?.('input') ?? null
}

/** Take the focus out of the field, if it can be found. */
export function blurInput(field: FieldRef): void {
	inputOf(field)?.blur()
}
