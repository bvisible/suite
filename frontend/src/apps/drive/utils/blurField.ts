//// Neoffice — added file (no upstream equivalent): the search field of Drive's toolbar, found again when its component
//// no longer exposes `el` (maintenance#1623). Escape threw "Cannot read properties of undefined (reading 'blur')" on every
//// press and never cleared the search.

type FieldRef = { el?: HTMLElement | null; $el?: HTMLElement | null } | null | undefined

/** The text input behind a frappe-ui TextInput ref: its `el` where it still exposes one, else its root, else the input inside it. */
export function inputOf(field: FieldRef): HTMLInputElement | null {
	const root = field?.el ?? field?.$el
	if (!root) return null
	if (root.tagName === 'INPUT') return root as HTMLInputElement
	return root.querySelector?.('input') ?? null
}

/** Take the focus out of the field, if it can be found. */
export function blurInput(field: FieldRef): void {
	inputOf(field)?.blur()
}
