import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import updateLocale from 'dayjs/plugin/updateLocale'

dayjs.extend(relativeTime)
dayjs.extend(updateLocale)

dayjs.updateLocale('en', {
	relativeTime: {
		future: 'in %s',
		past: '%s ago',
		s: 'few secs',
		m: 'a min',
		mm: '%d mins',
		h: 'an hr',
		hh: '%d hrs',
		d: 'a day',
		dd: '%d days',
		M: 'a mon',
		MM: '%d mons',
		y: 'a yr',
		yy: '%d yrs',
	},
})

export default dayjs
