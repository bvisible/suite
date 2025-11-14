import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import {
  absolutePositionToRelativePosition,
  relativePositionToAbsolutePosition,
  ySyncPluginKey,
} from 'y-prosemirror'

import * as Y from 'yjs'

const commentPluginKey = new PluginKey('comment-anchors')

const createDecorations = (editor, yDoc, comments, activeComment) => {
  if (!comments || !comments) return DecorationSet.empty

  const decorations = []
  const ystate = ySyncPluginKey.getState(editor.state)
  if (!ystate) return DecorationSet.empty
  const decos = []
  comments.forEach((comment) => {
    // Decode the stored relative position
    const relativePos = Y.decodeRelativePosition(comment.anchor)
    // Convert to absolute ProseMirror position
    const absPos = relativePositionToAbsolutePosition(
      yDoc,
      ystate.type,
      relativePos,
      ystate.binding.mapping,
    )
    const from = absPos
    const to = absPos + 1
    decos.push(
      Decoration.inline(from, to, {
        nodeName: 'span',
        class:
          comment.name === activeComment
            ? 'comment-highlight active'
            : 'comment-highlight',
        'data-comment-id': comment.id,
      }),
    )
  })
  return DecorationSet.create(editor.state.doc, decos)
}

const CommentHighlight = Extension.create({
  name: 'commentHighlight',

  addOptions() {
    return {
      comments: [],
      doc: null,
      activeComment: null,
      onActivated: null,
      edited: false,
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
            console.log(comments)
            return createDecorations(ext.editor, doc, comments, activeComment)
          },

          apply(tr, oldSet, oldState, newState) {
            // Check if we should rebuild decorations
            const shouldRebuild = true
            // tr.getMeta('commentsChanged') ||
            // tr.getMeta('activeCommentChanged') ||
            // tr.docChanged

            if (shouldRebuild) {
              const { doc, comments, activeComment } = ext.options
              return createDecorations(ext.editor, doc, comments, activeComment)
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

export default CommentHighlight
