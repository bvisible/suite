// Number-format grammar + renderer.
//
// Format string: `type[:variant][:decimals]`
//   currency           → currency, default USD, 2 decimals
//   currency:INR       → currency, INR, default decimals
//   currency:INR:0     → currency, INR, 0 decimals
//   currency:2         → currency, default variant, 2 decimals  ← legacy two-part form
//   number             → number, default (locale) thousands
//   number:in:0        → number, Indian lakhs grouping, 0 decimals
//   number:3           → number, default variant, 3 decimals    ← legacy
//   date               → date, default (locale)
//   date:dmy           → date, DD/MM/YYYY
//   time:hm12          → 3:30 PM
//   datetime:dmy:hm12  → 15/01/2025, 3:30 PM   (variant carries both halves)
//
// The parser disambiguates legacy two-part `type:N` (decimals-only) from
// new `type:variant` by checking whether the second token is digits-only.
// `type:variant:decimals` keeps both pieces explicit.

export function parseNumberFmt(fmt) {
  if (!fmt) return { type: '', variant: '', decimals: null }
  const parts = String(fmt).split(':')
  const type = parts[0]
  let variant = ''
  let decimals = null
  if (parts.length >= 3) {
    variant = parts[1]
    decimals = parts[2] !== '' ? parseInt(parts[2], 10) : null
  } else if (parts.length === 2) {
    const p = parts[1]
    if (/^-?\d+$/.test(p)) decimals = parseInt(p, 10)
    else variant = p
  }
  if (Number.isNaN(decimals)) decimals = null
  return { type, variant, decimals }
}

export function buildNumberFmt(type, variant, decimals) {
  if (!type) return ''
  const hasV = !!variant
  const hasD = decimals != null
  if (hasV && hasD) return `${type}:${variant}:${decimals}`
  if (hasV)        return `${type}:${variant}`
  if (hasD)        return `${type}:${decimals}`
  return type
}

// Supported currencies. `locale` drives symbol placement, thousand grouping,
// and decimal separator. `defaultDecimals` matters for JPY (whole yen) — the
// rest are 2 by default. Keep this list short on purpose; "More currencies"
// can be a follow-up.
export const CURRENCIES = {
  USD: { symbol: '$',  locale: 'en-US', defaultDecimals: 2 },
  EUR: { symbol: '€',  locale: 'de-DE', defaultDecimals: 2 },
  GBP: { symbol: '£',  locale: 'en-GB', defaultDecimals: 2 },
  INR: { symbol: '₹',  locale: 'en-IN', defaultDecimals: 2 },
  JPY: { symbol: '¥',  locale: 'ja-JP', defaultDecimals: 0 },
  CAD: { symbol: 'C$', locale: 'en-CA', defaultDecimals: 2 },
  AUD: { symbol: 'A$', locale: 'en-AU', defaultDecimals: 2 },
  CNY: { symbol: '¥',  locale: 'zh-CN', defaultDecimals: 2 },
}

// Number variant → locale used by Intl.NumberFormat. 'in' gives the Indian
// lakhs/crores grouping (12,34,56,789). '' means user-default locale.
const NUMBER_LOCALES = {
  '':   undefined,
  'us': 'en-US',
  'in': 'en-IN',
}

export function applyNumberFmt(value, format) {
  if (!format) return value
  const { type, variant, decimals } = parseNumberFmt(format)
  // Text format leaves the value untouched (no numeric coercion at display).
  // Cells flagged 'text' should also be treated as text in formulas; that's
  // handled by the engine's strict-arithmetic — see toNumStrict.
  if (type === 'text') return value == null ? '' : String(value)
  const n = parseFloat(value)
  if (isNaN(n) && type !== 'date') return value
  if (type === 'number') {
    const loc = NUMBER_LOCALES[variant] !== undefined ? NUMBER_LOCALES[variant] : undefined
    const opts = decimals == null ? {} : { minimumFractionDigits: decimals, maximumFractionDigits: decimals }
    return n.toLocaleString(loc, opts)
  }
  if (type === 'currency') {
    const code = CURRENCIES[variant] ? variant : 'USD'
    const cfg  = CURRENCIES[code]
    const d    = decimals ?? cfg.defaultDecimals
    return new Intl.NumberFormat(cfg.locale, { style: 'currency', currency: code, minimumFractionDigits: d, maximumFractionDigits: d }).format(n)
  }
  if (type === 'percentage') return (n * 100).toFixed(decimals ?? 2) + '%'
  if (type === 'date') {
    const d = parseFloat(value)
    return isNaN(d) ? value : new Date(d).toLocaleDateString()
  }
  return value
}
