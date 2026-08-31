import dayjs from 'dayjs/esm'
import isSameOrAfter from 'dayjs/esm/plugin/isSameOrAfter'
import isSameOrBefore from 'dayjs/esm/plugin/isSameOrBefore'
import isToday from 'dayjs/esm/plugin/isToday'
import isYesterday from 'dayjs/esm/plugin/isYesterday'
import localizedFormat from 'dayjs/esm/plugin/localizedFormat'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
import timezone from 'dayjs/esm/plugin/timezone'
import updateLocale from 'dayjs/esm/plugin/updateLocale'
import utc from 'dayjs/esm/plugin/utc'

dayjs.extend(updateLocale)
dayjs.extend(relativeTime)
dayjs.extend(localizedFormat)
dayjs.extend(isToday)
dayjs.extend(isYesterday)
dayjs.extend(isSameOrBefore)
dayjs.extend(isSameOrAfter)
// The APIs speak UTC while timestamps are shown in the user's own zone, so both are needed
// (`timezone` builds on `utc`, and this order is required).
dayjs.extend(utc)
dayjs.extend(timezone)

export default dayjs
