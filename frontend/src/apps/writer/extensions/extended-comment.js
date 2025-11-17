import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import {
  absolutePositionToRelativePosition,
  relativePositionToAbsolutePosition,
  ySyncPluginKey,
} from 'y-prosemirror'

import * as Y from 'yjs'

export const commentPluginKey = new PluginKey('comment-anchors')

const createDecorations = (editor, yDoc, comments, active) => {
  if (!comments || !comments) return DecorationSet.empty
  const ystate = ySyncPluginKey.getState(editor.state)
  if (!ystate) return DecorationSet.empty

  const decos = []
  comments.forEach((comment) => {
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
        class: comment.id === active && 'active',
        'data-comment-id': comment.id,
      }),
    )
  })
  return DecorationSet.create(editor.state.doc, decos)
}
export const CommentHighlight = Extension.create({
  name: 'commentHighlight',

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
            const { doc, comments, activeComment } = ext.options
            return createDecorations(
              ext.editor,
              doc,
              comments,
              activeComment.value,
            )
          },

          apply(tr, oldSet, oldState, newState) {
            const shouldRebuild = true
            if (shouldRebuild) {
              const { doc, comments, activeComment } = ext.options
              return createDecorations(
                ext.editor,
                doc,
                comments,
                activeComment.value,
              )
            }

            return oldSet
          },
        },
        props: {
          decorations(state) {
            return commentPluginKey.getState(state)
          },

          handleClick(view, pos, event) {
            const el = event.target.closest('[data-comment-id]')
            if (el) {
              const id = el.getAttribute('data-comment-id')
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
