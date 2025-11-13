import { Mark, mergeAttributes } from '@tiptap/core'

const DiffTag = Mark.create({
  name: 'diffTag',

  parseHTML() {
    return [
      { tag: 'ins', attrs: { type: 'insert' } },
    ]
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['ins', mergeAttributes(HTMLAttributes), 0]
  }
})

export default DiffTag