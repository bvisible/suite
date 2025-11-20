import { Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import TabView from './components/TabView.vue'
import {TextSelection} from '@tiptap/pm/state'
import { v4 } from 'uuid'

export const TabsExtension = Node.create({
  name: 'tab',
  group: 'block',
  content: 'block+',
  defining: true,
  isolating: true,

  addStorage() {
    return {
      activeTabId: null,
      hasInitialized: false,
    }
  },

  addOptions() {
    return {
      ydoc: null,
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
    const selectFirstTab = () => {
      if (this.storage.hasInitialized) return
      
      const { doc } = this.editor.state
      let firstTabId = null
      
      doc.descendants((node) => {
        if (node.type.name === 'tab' && !firstTabId) {
          firstTabId = node.attrs.id
          return false
        }
      })
      
      if (firstTabId) {
        this.storage.hasInitialized = true
        this.editor.commands.changeTab(firstTabId, false)
      }
    }
    selectFirstTab()
    // BROKEN: somehow stop constant re-firing of this
    this.editor.on('update', selectFirstTab)
  },

  onDestroy() {
    if (this.options.ydoc) {
      this.options.ydoc.off('sync', () => {})
    }
  },

  addCommands() {
    return {
      changeTab:
        (tabId: string, changed: boolean = true) =>
        ({ tr, dispatch, state }) => {
          if (this.editor.view.dom) {
            this.editor.view.dom.setAttribute(
              'data-active-tab',
              this.storage.activeTabId || '',
            )
          }
          this.storage.activeTabId = tabId
          dispatch(tr)
          if (changed)
            setTimeout(() => {
              let focusPos = null
              state.doc.descendants((node, pos) => {
                if (node.type.name === 'tab' && node.attrs.id === tabId) {
                  focusPos = pos + 1
                  return false
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
              return false
            }
          })

          if (updated) {
            dispatch(tr)
            return true
          }
          return false
        },
      wrapInTab:
        (attrs: { id?: string; label?: string } = {}) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            if (!attrs?.id) attrs.id = v4()
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

            dispatch(tr)
            this.editor.commands.changeTab(attrs.id)
          }
          return true
        },
    }
  },
 addKeyboardShortcuts() {
    return {
      'Mod-a': () => {
        const activeTabId = this.storage.activeTabId
        if (!activeTabId) return false

        const { state, view } = this.editor
        let tabStart = null
        let tabEnd = null

        state.doc.descendants((node, pos) => {
          if (node.type.name === 'tab' && node.attrs.id === activeTabId) {
            tabStart = pos + 1
            tabEnd = pos + node.nodeSize - 1
            return false
          }
        })

        if (tabStart !== null && tabEnd !== null) {
          const tr = state.tr.setSelection(
            TextSelection.create(state.doc, tabStart, tabEnd),
          )
          view.dispatch(tr)
          return true
        }

        return false
      },
    }
  },
})