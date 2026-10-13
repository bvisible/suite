// //// Neoffice — added file (no upstream equivalent): relative times in the reader's language.
// //// vueuse's useTimeAgo writes its own English ("just now", "2 minutes ago") whatever the account's language
// //// (dateLocale.ts makes dayjs speak it, not vueuse): the Drive's last-modified column, Writer's lists and the date
// //// of an open mail read English on a French desk. useTimeAgoIntl hands the phrase to Intl.RelativeTimeFormat in the
// //// language of the page (<html lang>, www/suite.py): « il y a 2 minutes », « hier ».
import { useTimeAgoIntl } from '@vueuse/core'
import type { MaybeRefOrGetter } from 'vue'

export function timeAgo(time: MaybeRefOrGetter<Date | number | string>) {
  return useTimeAgoIntl(time, { locale: document.documentElement.lang || undefined })
}
