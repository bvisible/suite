// //// Neoffice — added file (no upstream equivalent): clock times in the reader's language (maintenance#1321).
// //// Upstream writes its times with US patterns (`h:mm a`, `h:mm A`), so a French account read « 3:00 pm » beside
// //// French month names. A locale with a 24-hour clock (fr, de, it: dayjs' `LT` is `HH:mm`) gets `LT`; English
// //// keeps upstream's own patterns, its compact « 3:00 – 4:00 pm » included.

/** What both copies of dayjs (`dayjs` and `dayjs/esm`) share, enough to ask a locale for its clock. */
interface Clock {
  hour(value: number): Clock
  minute(value: number): Clock
  format(template?: string): string
}

/** Whether the active dayjs locale writes a meridiem (am/pm): 13:00 read through its `LT`. A copy of dayjs without
 *  the localizedFormat plugin prints « LT » as it is, and keeps upstream's patterns. */
export const usesMeridiem = (day: Clock): boolean => !day.hour(13).minute(0).format('LT').includes('13')

/** `day` as a clock time: upstream's 12-hour `pattern` where the locale has a meridiem, `pattern24` elsewhere. */
export const clockTime = (day: Clock, pattern = 'h:mm a', pattern24 = 'LT'): string =>
  day.format(usesMeridiem(day) ? pattern : pattern24)
