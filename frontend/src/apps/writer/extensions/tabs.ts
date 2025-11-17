import { Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import TabView from './components/TabView.vue'
import { v4 } from 'uuid'

export const TabsExtension = Node.create({
  name: 'tab',
  group: 'block',
  content: 'block+',

  addStorage() {
    return {
      activeTabId: null,
    }
  },
  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-tab-id'),
        renderHTML: (attrs) => (attrs.id ? { 'data-tab-id': attrs.id } : {}),
      },
      label: {
        default: 'Untitled',
        parseHTML: (el) => el.getAttribute('data-tab-label'),
        renderHTML: (attrs) => ({ 'data-tab-label': attrs.label }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-tab-id]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', HTMLAttributes, 0]
  },

  addNodeView() {
    return VueNodeViewRenderer(TabView)
  },

  onCreate() {
    // Select first tab on mount
    const { doc } = this.editor.state
    let set = false
    doc.descendants((node) => {
      if (!set && node.type.name === 'tab') {
        this.editor.commands.changeTab(node.attrs.id)
        set = true
      }
    })
  },

  addCommands() {
    return {
      changeTab:
        (tabId: string) =>
        ({ tr, dispatch, state }) => {
          if (this.editor.view.dom) {
            this.editor.view.dom.setAttribute(
              'data-active-tab',
              this.storage.activeTabId || '',
            )
          }
          this.storage.activeTabId = tabId
          dispatch(tr)
          setTimeout(() => {
            let focusPos = null
            state.doc.descendants((node, pos) => {
              if (node.type.name === 'tab' && node.attrs.id === tabId) {
                // Focus at the start of the tab's content (pos + 1)
                focusPos = pos + 1
                return false // Stop searching
              }
            })

            if (focusPos !== null) {
              this.editor.commands.focus(focusPos)
            }
          }, 0)
          return true
        },
      getCurrentTab: () => () => this.storage.activeTabId,
      renameTab:
        (tabId: string, newLabel: string) =>
        ({ tr, dispatch, state }) => {
          if (!dispatch) return false

          let updated = false
          state.doc.descendants((node, pos) => {
            if (node.type.name === 'tab' && node.attrs.id === tabId) {
              tr.setNodeMarkup(pos, undefined, {
                ...node.attrs,
                label: newLabel,
              })
              updated = true
              return false // Stop traversing
            }
          })

          if (updated) {
            dispatch(tr)
            return true
          }
          return false
      },
      wrapInTab:
        (attrs: { id: string; label: string }) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            if (!attrs.id) attrs.id = v4()
            const tabType = this.editor.schema.nodes.tab
            tr.replaceWith(
              0,
              tr.doc.content.size,
              tabType.create(attrs, tr.doc.content),
            )
            this.storage.activeTabId = attrs.id
            dispatch(tr)
            return true
          }
        },
      createTab:
        (attrs: { id: string; label: string }) =>
        ({ tr, dispatch, state }) => {
          if (dispatch) {
            const paragraphType = this.editor.schema.nodes.paragraph
            if (!attrs.id) attrs.id = v4()
            const tab = this.editor.schema.nodes.tab.create(
              attrs,
              paragraphType.create(),
            )
            tr.insert(state.doc.content.size, tab)

            this.storage.activeTabId = attrs.id
            dispatch(tr)
          }
          return true
        },
    }
  },
})
