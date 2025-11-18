<template>
  <div
    ref="scrollContainer"
    class="relative hidden md:flex flex-col gap-8 justify-start self-stretch px-5 bg-surface-white"
  >
    <template v-for="comment in filteredComments" :key="comment.id">
      <div
        :id="'comment-' + comment.id"
        :ref="
          (el) => {
            if (el) commentRefs[comment.id] = el
            else delete commentRefs[comment.id]
          }
        "
        v-on-outside-click="
          (e) => {
            console.log(comment)
            if (
              activeComment === comment.id &&
              !e.target.getAttribute('data-comment-name') &&
              e.target.nodeName === 'DIV' &&
              !comment.new &&
              !e.target.classList?.contains?.('replies-count')
            )
              activeComment = null
          }
        "
        class="absolute rounded shadow w-52 md:w-72 comment-group scroll-m-24 bg-surface-white opacity-0 transition-[top] duration-100 ease-in-out"
        :class="[
          activeComment === comment.id && 'shadow-xl ',
          comment.top && 'opacity-100',
        ]"
        :style="`top: ${comment.top}px;`"
        @click="activeComment = comment.id"
      >
        <div
          v-show="
            activeComment === comment.id &&
            $store.state.user.id !== 'Guest' &&
            !comment.new &&
            (comment.owner == $store.state.user.id || document.doc.write)
          "
          class="p-1.5 text-sm flex gap-1 border-b text-ink-gray-9"
          :class="comment.loading && !comment.edit && 'opacity-70'"
        >
          <Button
            v-if="
              !comment.resolved &&
              (comment.owner == $store.state.user.id || document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="resolve(comment)"
          >
            <template #prefix>
              <LucideCheck class="size-3.5" />
            </template>
            Resolve
          </Button>
          <Button
            v-if="
              comment.resolved &&
              (comment.owner == $store.state.user.id || document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="resolve(comment, false)"
          >
            <template #prefix>
              <LucideMessageCircleCode class="size-3.5" />
            </template>
            Unresolve
          </Button>
          <Button
            v-if="
              comment.owner == $store.state.user.id ||
              (comment.owner === 'Guest' && document.doc.write)
            "
            :disabled="comment.loading"
            variant="ghost"
            class="!h-5 !text-xs !px-1.5 !rounded-sm"
            @click="removeComment(comment.id, true)"
          >
            <template #prefix>
              <LucideX class="size-3.5" />
            </template>
            Delete
          </Button>
        </div>
        <div
          class="flex flex-col gap-5 p-3"
          :class="
            activeComment !== comment.id &&
            comment.replies.length > 0 &&
            'pb-1.5'
          "
        >
          <div
            v-for="(reply, index) in activeComment === comment.id
              ? [
                  comment,
                  ...comment.replies.toSorted((a, b) =>
                    new Date(a.creation) > new Date(b.creation) ? 1 : -1,
                  ),
                ]
              : [comment]"
            :key="reply.name || reply.id"
            class="group flex-grow flex gap-3"
            :class="reply.loading && !reply.edit && 'opacity-70'"
          >
            <div class="w-8 flex justify-center">
              <Avatar
                size="xl"
                class="bg-surface-white"
                :label="$user(reply.owner)?.full_name || reply.owner"
                :image="$user(reply.owner)?.user_image"
              />
            </div>
            <div
              class="grow flex flex-col min-w-0"
              :class="reply.edit && 'gap-1'"
            >
              <div
                class="w-full flex justify-between items-start label-group gap-1 text-sm"
              >
                <div class="flex gap-1">
                  <label
                    class="font-medium text-ink-gray-8 max-w-[70%] truncate"
                    >{{ $user(reply.owner)?.full_name || reply.owner }}</label
                  >

                  <label class="text-ink-gray-6 truncate">
                    &#183;
                    {{ formatDateOrTime(reply.creation) }}</label
                  >
                </div>
                <Dropdown
                  class="ml-auto opacity-0"
                  :class="
                    activeComment === comment.id &&
                    !reply.edit &&
                    !reply.resolved &&
                    comment.owner == $store.state.user.id &&
                    'opacity-100'
                  "
                  :options="
                    dynamicList([
                      {
                        label: 'Edit',
                        onClick: () => (reply.edit = true),
                        cond: comment.owner == $store.state.user.id,
                      },
                      {
                        label: 'Delete',
                        onClick: () => removeReply(comment.id, reply.id),
                        cond:
                          comment.owner == $store.state.user.id && index !== 0,
                      },
                    ])
                  "
                >
                  <Button
                    :disabled="
                      activeComment !== comment.id ||
                      reply.edit ||
                      reply.resolved
                    "
                    class="!h-5 !text-xs !px-1.5 !rounded-sm opacity-0"
                    :class="
                      activeComment === comment.id &&
                      !reply.edit &&
                      !reply.resolved &&
                      comment.owner == $store.state.user.id &&
                      'opacity-100'
                    "
                    variant="ghost"
                    :icon="h(LucideMoreVertical, { class: 'size-3' })"
                    @click="triggerRoot"
                  />
                </Dropdown>
                <LucideBadgeCheck
                  v-if="comment.resolved"
                  class="text-ink-gray-6 size-4"
                />
              </div>
              <div class="comment-content text-sm">
                <CommentEditor
                  v-model="commentContents[reply.id]"
                  placeholder="Edit"
                  :disabled="
                    isEmpty(commentContents[reply.id]) ||
                    commentContents[reply.id] == reply.text
                  "
                  :editable="!!(reply.edit || reply.new)"
                  :content="reply.text"
                  @change="setCommentHeights"
                  @submit="
                    () => {
                      updateComment(reply, comment)
                    }
                  "
                  @cancel="
                    (editor) => {
                      if (reply.new) {
                        removeComment(reply.id)
                      } else {
                        editor.commands.setContent(reply.text)
                        reply.edit = false
                      }
                    }
                  "
                />
              </div>
            </div>
          </div>

          <div
            v-show="
              activeComment === comment.id &&
              !(comment.edit || comment.new) &&
              !comment.resolved
            "
            class="flex gap-3"
          >
            <Avatar
              size="xl"
              class="self-center"
              :label="
                $user($store.state.user.id)?.full_name || $store.state.user.id
              "
              :image="$user($store.state.user.id)?.user_image"
            />

            <CommentEditor
              v-model="newReplies[comment.id]"
              placeholder="Reply"
              :is-empty="isEmpty(newReplies[comment.id])"
              @change="setCommentHeights"
              @submit="(editor) => newReply(comment, editor)"
              @cancel="
                (editor) => {
                  newReplies[comment.id] = ''
                  editor.commands.setContent('')
                  editor.commands.blur()
                }
              "
            />
          </div>
        </div>
        <div
          v-if="activeComment !== comment.id && comment.replies.length > 0"
          class="replies-count text-ink-gray-6 font-base text-xs p-3 pt-0"
        >
          {{ comment.replies.length }}
          {{ comment.replies.length === 1 ? 'reply' : 'replies' }}
        </div>
      </div>
    </template>
  </div>
</template>
<script setup>
import {
  computed,
  reactive,
  watch,
  inject,
  onMounted,
  ref,
  h,
  onBeforeUnmount,
  nextTick,
} from 'vue'
import { Avatar, Button, createResource, Dropdown } from 'frappe-ui'
import { formatDate } from '@/utils/format'
import { dynamicList } from '@/utils/'
import { v4 } from 'uuid'
import { useDebounceFn, useEventListener } from '@vueuse/core'
import LucideX from '~icons/lucide/x'
import LucideMoreVertical from '~icons/lucide/more-vertical'
import store from '@/store'
import CommentEditor from './CommentEditor.vue'

const props = defineProps({
  document: Object,
  editor: Object,
  yComments: Object,
})
const emit = defineEmits(['save'])

const activeComment = defineModel('activeComment')
const scrollContainer = ref('scrollContainer')

const newReplies = reactive({})
const commentRefs = reactive({})
const commentContents = reactive({})

function useYMapReactive(yMap) {
  const local = ref([])

  const update = () => {
    const arr = []
    yMap.forEach((v) => {
      arr.push(v)
      console.log(v.id, v.text)
    })
    local.value = arr
  }

  update()
  yMap.observe(update)

  onBeforeUnmount(() => yMap.unobserve(update))

  return local
}
const comments = useYMapReactive(props.yComments)

const showResolved = inject('showResolved')
const filteredComments = computed(() => {
  const filtered = showResolved.value
    ? comments.value
    : comments.value.filter((k) => !k.resolved)
  return filtered
})

watch(showResolved, async (val) => {
  await nextTick()
  if (val) {
    document
      .querySelectorAll('[data-resolved=true]')
      .forEach((k) => k.classList.add('display'))
  } else {
    document
      .querySelectorAll('[data-resolved=true]')
      .forEach((k) => k.classList.remove('display'))
  }
})

watch(activeComment, (val) => {
  setCommentHeights()
})

const resolveComment = createResource({
  url: '/api/method/drive.api.docs.resolve_comment',
  onSuccess: () => {
    emit('save')
  },
})

const sanitize = (comment) => {
  delete comment.new
  comment.edit = false
  const obj = { ...comment }
  delete obj.edit
  delete obj.new
  delete obj.top
  return obj
}

const updateComment = (comment, thread) => {
  comment.text = commentContents[comment.id]
  comment.edit = false
  if (comment.id === thread.id) {
    props.yComments.set(comment.id, sanitize(comment))
  } else {
    thread.replies = thread.replies.map((r) =>
      r.id === comment.id ? sanitize(comment) : r,
    )
    props.yComments.set(thread.id, sanitize(thread))
  }
  emit('save')
}

const newReply = (comment, editor) => {
  const id = v4()
  const reply = {
    id,
    text: newReplies[comment.id],
    owner: store.state.user.id,
    creation: Date.now(),
  }
  comment.replies.push(reply)
  props.yComments.set(comment.id, comment)

  editor.commands.setContent('')
  setCommentHeights()
  emit('save')
}

const removeReply = (commentId, replyId) => {
  const comment = comments.value.find((c) => c.id === commentId)
  if (!comment) return

  // Update Yjs map
  const updatedReplies = comment.replies.filter((r) => r.id !== replyId)
  const updatedComment = { ...comment, replies: updatedReplies }
  props.yComments.set(commentId, updatedComment)

  setCommentHeights()
  emit('save')
}

const removeComment = (commentId) => {
  props.yComments.delete(commentId)
  setCommentHeights()
  emit('save')
}

const resolve = (comment, value = true) => {
  // Update Yjs map
  const updatedComment = { ...comment, resolved: value }
  props.yComments.set(comment.id, updatedComment)

  // Update editor marks
  props.editor.commands.resolveComment(comment.id, value)

  // Submit to server
  resolveComment.submit({ name: comment.id, value })
}

const isEmpty = (editorContent) => {
  return (
    !editorContent ||
    !editorContent.length ||
    editorContent.replace(/\s/g, '') == '<p></p>'
  )
}

const formatDateOrTime = (datetimeNum) => {
  const now = new Date()
  const datetime = new Date(datetimeNum)
  const isToday =
    datetime.getDate() === now.getDate() &&
    datetime.getMonth() === now.getMonth() &&
    datetime.getFullYear() === now.getFullYear()
  const [dateStr, timeStr] = formatDate(datetime).split(', ')
  return isToday ? timeStr : dateStr
}

const setCommentHeights = useDebounceFn(() => {
  let lastBottom = 0
  nextTick(() => {
    // scrollContainer.value.style.height = `max(${scrollContainer.value.parentElement.scrollHeight}px, calc(100vh - 3rem))`
    for (const comment of filteredComments.value) {
      try {
        const containerTop = scrollContainer.value.getBoundingClientRect().top
        const el =
          document.querySelector(`[data-comment-name="${comment.id}"]`) ||
          document.querySelector(`[data-comment-id="${comment.id}"]`)
        const anchorTop = el.getBoundingClientRect().top - containerTop
        const adjustedTop = Math.max(anchorTop, lastBottom)
        comment.top = adjustedTop
        lastBottom = adjustedTop + commentRefs[comment.id].offsetHeight + 12
      } catch (e) {
        console.log(e)
      }
    }
  })
}, 20)

onMounted(setCommentHeights)
watch(() => filteredComments.value.length, setCommentHeights)
useEventListener(window, 'resize', setCommentHeights)

props.editor.on('update', () => {
  const currentNames = new Set()
  setCommentHeights()
  props.editor.state.doc.descendants((node) => {
    node.marks.forEach((mark) => {
      if (mark.type.name === 'comment' && mark.attrs.commentId) {
        currentNames.add(mark.attrs.commentId)
      }
    })
  })
})

const purgeNewEmptyComments = () => {
  for (const comment of comments.value)
    if (comment.new) removeComment(comment.id, true)
}

onBeforeUnmount(purgeNewEmptyComments)
useEventListener(window, 'beforeunload', purgeNewEmptyComments)
</script>
