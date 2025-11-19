import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import {
  relativePositionToAbsolutePosition,
  ySyncPluginKey,
} from 'y-prosemirror'

import * as Y from 'yjs'
export const commentPluginKey = new PluginKey('comment-anchors')

export const rebuild = (editor) => {
  editor
    .chain()
    .command(({ tr }) => {
      tr.setMeta(commentPluginKey, { rebuild: true })
      return true
    })
    .run()
}

const createDecorations = (editor, yDoc, comments, active, showResolved) => {
  if (!comments._map.size) return DecorationSet.empty
  const ystate = ySyncPluginKey.getState(editor.state)
  if (!ystate) return DecorationSet.empty
  const decos = []
  comments.forEach((comment) => {
    if (!comment.anchor.from || (!showResolved && comment.resolved)) return
    const from = relativePositionToAbsolutePosition(
      yDoc,
      ystate.type,
      Y.decodeRelativePosition(comment.anchor.from),
      ystate.binding.mapping,
    )
    const to = relativePositionToAbsolutePosition(
      yDoc,
      ystate.type,
      Y.decodeRelativePosition(comment.anchor.to),
      ystate.binding.mapping,
    )
    decos.push(
      Decoration.inline(from, to, {
        nodeName: 'span',
        class: comment.id === active ? 'active' : '',
        'data-comment-name': comment.id,
        'data-resolved': comment.resolved,
      }),
    )
  })
  return DecorationSet.create(editor.state.doc, decos)
}
export const CommentExtension = Extension.create({
  name: 'commentExtension',

  addOptions() {
    return {
      comments: [],
      doc: null,
      activeComment: null,
      onActivated: null,
    }
  },

  addProseMirrorPlugins() {
    const ext = this

    return [
      new Plugin({
        key: commentPluginKey,
        state: {
          init(_, state) {
            const { doc, comments, activeComment, showResolved, showComments } =
              ext.options
            if (!showComments.value) return DecorationSet.empty
            return createDecorations(
              ext.editor,
              doc,
              comments,
              activeComment.value,
              showResolved.value,
            )
          },

          apply(tr, oldSet) {
            const { doc, comments, activeComment, showResolved, showComments } =
              ext.options
            if (!showComments.value) return DecorationSet.empty

            const isRemote = tr.getMeta('y-sync$')?.isChangeOrigin
            if (isRemote || tr.getMeta(commentPluginKey)?.rebuild) {
              const decos = createDecorations(
                ext.editor,
                doc,
                comments,
                activeComment.value,
                showResolved.value,
              )
              return decos
            }

            return oldSet.map(tr.mapping, tr.doc)
          },
        },
        props: {
          decorations(state) {
            return commentPluginKey.getState(state)
          },

          handleClick(view, pos, event) {
            const el = event.target.closest('[data-comment-name]')
            if (el) {
              const id = el.getAttribute('data-comment-name')
              ext.options.onActivated?.(id)
              return true
            }
            return false
          },
        },
      }),
    ]
  },
})
