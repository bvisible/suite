import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { DriveDocument } from '@/types/doctypes'
import { prettyData } from 'frappe-ui/frappe/drive/js/utils'

let docsCache: Record<string, ReturnType<typeof useDoc>> = {}

export default function useDocument(docId: MaybeRefOrGetter<string>) {
  interface Document extends DriveDocument {}

  interface DocumentMethods {
    // trackVisit: () => void
  }

  let name = toValue(docId)
  if (!docsCache[name]) {
    docsCache[name] = useDoc<Document, DocumentMethods>({
      doctype: 'Drive File',
      url: '/api/method/writer.api.docs.get_document?file_id=' +docId,
      name: docId,
      transform: prettyData,
      methods: {
        trackVisit: 'track_visit',
      },
    })
  }
  return docsCache[name] as ReturnType<typeof useDoc<Document, DocumentMethods>>
}
