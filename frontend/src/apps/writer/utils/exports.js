import { createResource } from 'frappe-ui'
import { toast } from '@/utils'

export const exportMedia = async (editor) => {
  toast('Preparing...')
  const urls = editor.commands.getEmbedUrls()
  const getExtension = createResource({
    url: 'drive.api.docs.get_extension',
  })
  console.log(urls)
  for (const i in urls) {
    const ext = await getExtension.fetch({ entity_name: urls[i].name })
    if (ext) urls[i].title += '.' + ext
  }
  entitiesDownload(null, urls)
}

export const exportBlog = async () => {
  toast('Starting export...')
  createResource({
    url: 'drive.api.docs.create_blog',
    auto: true,
    params: {
      entity_name: props.id,
      html: editorValue.value.getHTML(),
    },
    onSuccess: (d) => {
      window.open('/app/blog-post/' + d)
    },
    onError: (error) => {
      toast({
        title: error.messages[0] || 'Could not export your document.',
        type: 'error',
      })
    },
  })
}
