// Cell text-wrap modes. Replaces the legacy boolean `wrapText` with a
// three-way enum that matches Sheets / Excel semantics:
//
//   'overflow' — long text spills into adjacent empty cells (default)
//   'clip'     — hard truncate at the cell border
//   'wrap'     — word-wrap inside the cell, row auto-grows
//
// Backwards compat: when only the old `wrapText: boolean` is set,
// `true` → 'wrap', `false`/missing → 'overflow'. New writes always
// use `textWrap`; old cells keep working until they're re-saved.

export const WRAP_MODES = ['overflow', 'clip', 'wrap']

export function getTextWrap(fmt) {
  if (!fmt) return 'overflow'
  if (WRAP_MODES.includes(fmt.textWrap)) return fmt.textWrap
  if (fmt.wrapText === true) return 'wrap'
  return 'overflow'
}

export function isWrapText(fmt) {
  return getTextWrap(fmt) === 'wrap'
}
