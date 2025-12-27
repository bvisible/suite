<template>
  <!-- Mutation dialogs -->
  <RenameDialog
    v-if="dialog === 'rn'"
    v-model="dialog"
    :entity="entities[0]"
    @success="
      ({ title }) => {
        entities[0].title = title
        entities[0].breadcrumbs[entities[0].breadcrumbs.length - 1].title =
          title
        resetDialog()
      }
    "
  />
  <ShareDialog
    v-else-if="dialog === 's'"
    v-model="dialog"
    :add-users="params || []"
    :entity="entities[0]"
    @success="
      () => {
        resource.fetch(resource.params)
      }
    "
  />
  <MoveDialog
    v-else-if="dialog === 'm'"
    v-model="dialog"
    :entities="entities"
    @complete="entity_open && resource.fetch(resource.params)"
  />
  <InfoDialog
    v-else-if="dialog === 'i'"
    v-model="dialog"
    :entity="entities[0]"
    :emitter
  />

  <!-- Confirmation dialogs -->
  <RemoveDialog
    v-if="dialog === 'remove'"
    v-model="dialog"
    :entities="entities"
    @success="$router.push({ name: 'Home' })"
  />

  <SearchDialog v-if="dialog === 'search'" v-model="dialog"/>
</template>
<script setup>
import { ref, watch, computed } from 'vue'
import { useStore } from 'vuex'

import emitter from '@/emitter'

import {
  ShareDialog,
  MoveDialog,
  InfoDialog,
  RenameDialog,
} from 'frappe-ui/frappe/drive'
import RemoveDialog from './RemoveDialog.vue'
import SearchDialog from './SearchDialog.vue'
import { onKeyDown } from '@vueuse/core'

const props = defineProps({
  document: Object,
  entities: Array,
})
const store = useStore()
const listResource = computed(() => store.state.listResource)
const resource = computed(() =>
  store.state.currentResource && Object.keys(store.state.currentResource).length
    ? store.state.currentResource
    : listResource.value,
)
const entity_open = computed(
  () =>
    resource.value.data?.name &&
    props.entities[0]?.name === resource.value.data?.name,
)

const dialog = defineModel(String)
const params = ref(null)
const open = ref(false)
watch(dialog, (val) => {
  if (val) open.value = true
})

const resetDialog = () => (dialog.value = '')

emitter.on('share', (data) => {
  params.value = data
  dialog.value = 's'
})
emitter.on('newFolder', () => (dialog.value = 'f'))
emitter.on('rename', () => (dialog.value = 'rn'))
emitter.on('remove', () => (dialog.value = 'remove'))
emitter.on('move', () => (dialog.value = 'm'))
emitter.on('newLink', () => (dialog.value = 'l'))

onKeyDown('k', (e) => {
  console.log(e, e.metaKey && e.shiftKey)
  if (e.metaKey && e.shiftKey) {
    e.preventDefault()
    dialog.value = 'search'
  }
})
</script>
