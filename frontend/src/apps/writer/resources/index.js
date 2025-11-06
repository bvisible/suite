import { useList } from 'frappe-ui'
import { prettyData } from '@/utils'

export const getDocuments = useList({
  url: '/api/method/writer.api.general.get_document_list',
  start: 0,
  limit: 50,
  immediate: true,
  cacheKey: 'writer-document-list',
  transform: (data) => {
    return prettyData(data)
  },
})
