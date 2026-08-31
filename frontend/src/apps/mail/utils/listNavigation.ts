import { ref } from 'vue'

// Shared pieces of keyboard list navigation, for the two thread lists and the screener. Only
// what is genuinely identical lives here: which keys navigate, which direction each means, how
// to step a cursor through a list, and the `g` prefix. Every export below has more than one
// caller — anything that ended up with one has been inlined where it is used.
//
// The handlers themselves stay in the views, because what a step *does* differs — the mailbox
// list steps over stacks and day headers and extends a shift-selection, the merged list steps
// over flat rows and has no selection at all. Threading that through one function would take
// more callbacks than it would save.

/** Keys that move the cursor. Compared against a lowercased `event.key`. */
const NAVIGATION_KEYS = ['arrowup', 'arrowdown', 'j', 'k']

export const isNavigationKey = (key: string) => NAVIGATION_KEYS.includes(key)

/** Up/k walk backwards, down/j forwards. */
export const navigationOffset = (key: string) => (['arrowup', 'k'].includes(key) ? -1 : 1)

/**
 * The row `offset` steps from the one keyed `currentKey`.
 *
 * A `currentKey` that is no longer in the list — a row folded away, or removed by a mutation —
 * restarts from the first row rather than losing the cursor. Returns undefined at the ends, which
 * is how a caller knows to load the next window instead (see `hasCursor` for telling the two apart).
 */
export const stepFromKey = <T extends { key: string }>(
	rows: T[],
	currentKey: string | undefined,
	offset: number,
): T | undefined => {
	const index = rows.findIndex((row) => row.key === currentKey)
	return index === -1 ? rows[0] : rows[index + offset]
}

/** Whether the cursor is currently on a known row — the ends need distinguishing from "lost". */
export const hasCursor = <T extends { key: string }>(rows: T[], currentKey: string | undefined) =>
	rows.some((row) => row.key === currentKey)

/**
 * The `g` prefix: `g g` jumps to the first entry, `G` to the last. A lone `g` arms for
 * this long, then forgets — so `g`, pause, `g` is two separate presses, not a jump.
 */
const G_PREFIX_WINDOW_MS = 750

/**
 * State machine for that prefix. `press` reports the intent and leaves acting on it to the
 * caller, because "first" means the first row in one list and the first thread in another.
 */
export const useGPrefix = () => {
	const armed = ref(false)
	let timer: ReturnType<typeof setTimeout> | undefined

	const disarm = () => {
		clearTimeout(timer)
		armed.value = false
	}

	const press = (shiftKey: boolean): 'first' | 'last' | 'armed' => {
		// Shift+G is a jump in its own right, so it also clears any half-typed `g`.
		if (shiftKey) {
			disarm()
			return 'last'
		}
		if (armed.value) {
			disarm()
			return 'first'
		}
		clearTimeout(timer)
		armed.value = true
		timer = setTimeout(() => (armed.value = false), G_PREFIX_WINDOW_MS)
		return 'armed'
	}

	return { armed, press, disarm }
}
