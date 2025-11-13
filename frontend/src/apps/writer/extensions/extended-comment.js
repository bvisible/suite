import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin } from '@tiptap/pm/state'

const CommentHighlight = Extension.create({
  name: 'commentHighlight',

  addOptions() {
    return {
      comments: [],
      onActivated: null,
      activeComment: null,
    }
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations: (state) => {
            const { comments, activeComment } = this.options
            if (!comments || !comments.length) return null
            const decorations = comments.map((comment) =>
              Decoration.inline(comment.anchor.from, comment.anchor.to, {
                nodeName: 'span',
                class: comment.name === activeComment.value ? 'active' : '',
                'data-comment-id': comment.name,
              }),
            )
            return DecorationSet.create(state.doc, decorations)
          },

          handleClick: (view, pos, event) => {
            const el = event.target.closest('[data-comment-id]')
            if (el) {
              const id = el.getAttribute('data-comment-id')
              this.options.onActivated(id)
              return true
            }
            return false
          },
        },
      }),
    ]
  },
})

export default CommentHighlight
