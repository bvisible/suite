export function formatSize(size, nDigits = 1) {
  if (size === 0) return '0 KB'
  var i = -1
  var byteUnits = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  do {
    size /= 1000
    i++
  } while (size > 1000)
  return Math.max(size, 0.1).toFixed(nDigits) + ' ' + byteUnits[i]
}

export function base2BlockSize(bytes) {
  if (bytes === 0) return '0 bytes'
  const k = 1024
  const sizes = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatDate(date) {
  if (!date) return ''
  const dateObj = new Date(date)
  //// Neoffice — the account's language (<html lang>, set by www/suite.py) in place of upstream's 'en-US', so a French
  //// account reads 08/10/26, 14:30 and not 10/08/26, 02:30 PM (maintenance#1321).
  const lang = document.documentElement.lang || 'en-US'
  const formattedDate = new Intl.DateTimeFormat(lang, {
    month: '2-digit',
    day: '2-digit',
    year: '2-digit',
  }).format(dateObj)
  //// Neoffice — the account's language, see above (maintenance#1321).
  const formattedTime = new Intl.DateTimeFormat(lang, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(dateObj)
  return `${formattedDate}, ${formattedTime}`
}

export const formatPercent = (num) => {
  return new Intl.NumberFormat('default', {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(num / 100)
}

export const COLOR_MAP = {
  Archive: '#C2A88D',
  Application: '#f472b6',
  Image: '#34BAE3',
  Video: '#E86C13',
  Audio: '#9C45E3',
  Document: '#0073CA',
  Spreadsheet: '#30A66D',
  Presentation: '#F5BA14',
  Text: '#E2E2E2',
  PDF: '#E03636',
  Book: '#E2E2E2',
  Unknown: '#3f3f46',
}
