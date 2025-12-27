<template>
  <div
    ref="container"
    class="mx-auto w-96 sm:w-[60%] pt-8 h-screen space-y-3 pb-64"
  >
    <template
      v-for="([group, files], i) in Object.entries(groups)"
      :key="group"
    >
      <div v-if="files.length" class="space-y-0.5">
        <div
          class="flex justify-between items-center sticky top-0 bg-surface-white h-10 z-10"
        >
          <h2 class="text-sm font-medium text-ink-gray-5">
            {{ group }}
          </h2>
          <TabButtons
            v-if="i === 0"
            class="w-fit"
            v-model="thumbnail"
            :buttons="[
              {
                label: 'Grid',
                value: 'grid',
                icon: LucideGrid,
                hideLabel: true,
              },
              {
                label: 'List',
                value: 'list',
                icon: LucideList,
                hideLabel: true,
              },
            ]"
          />
        </div>
        <div
          :class="
            thumbnail === 'grid' &&
            'grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 !mb-0 mx-0.5'
          "
        >
          <div v-for="(row, i) in files" :key="row.name">
            <template v-if="thumbnail === 'grid'">
              <section
                class="group"
                @click="
                  $router.push({ name: 'Document', params: { id: row.name } })
                "
              >
                <div
                  class="aspect-[37/50] cursor-pointer overflow-hidden rounded-md dark:bg-gray-900 border border-gray-50 dark:border-outline-gray-1 px-2.5 py-1 shadow-lg transition-shadow hover:shadow-xl"
                >
                  <div class="overflow-hidden text-ellipsis whitespace-nowrap">
                    <div
                      class="prose prose-sm prose-v2 pointer-events-none w-[200%] origin-top-left scale-[.55] prose-p:my-1 md:w-[250%] md:scale-[.39]"
                      v-html="row.html"
                    />
                  </div>
                </div>
                <div class="mt-3 flex justify-between items-center">
                  <div class="flex-grow w-full min-w-0">
                    <h1 class="text-base truncate font-medium text-ink-gray-7">
                      {{ row.title }}
                    </h1>
                  </div>
                  <div class="shrink-0 ml-1 invisible group-hover:visible">
                    <Dropdown
                      :button="{
                        icon: 'more-horizontal',
                        label: 'Page Options',
                        variant: 'ghost',
                      }"
                      :options="[]"
                    />
                  </div>
                </div>
              </section>
            </template>
            <template v-else>
              <div
                @click="
                  $router.push({ name: 'Document', params: { id: row.name } })
                "
                class="group flex items-center justify-between px-3 h-10 py-3 hover:bg-surface-gray-1 rounded cursor-pointer my-px -mx-3"
              >
                <div class="flex flex-col gap-1 w-[60%]">
                  <p class="text-sm font-medium text-ink-gray-8 truncate">
                    {{ row.title }}
                  </p>
                  <!-- <div class="text-xs text-ink-gray-5">
                    {{ row.file_size_pretty }}
                  </div> -->
                </div>

                <div
                  class="flex items-center gap-2 text-sm text-gray-600 flex-shrink-0"
                >
                  <div
                    v-if="row.owner !== $store.state.user.id"
                    class="text-xs text-ink-gray-5 flex gap-5 items-center"
                  >
                    <LucideGlobe2
                      v-if="row.share_count == -2"
                      class="size-4 text-ink-gray-6"
                    />
                    <LucideBuilding2
                      v-else-if="row.share_count == -1"
                      class="size-4 text-ink-gray-6"
                    />
                    <LucideUsers
                      v-else-if="row.share_count > 0"
                      class="size-4 text-ink-gray-6"
                    />
                    <div
                      v-if="row.owner != $store.state.user.id"
                      class="flex items-center gap-1 w-32 justify-start"
                    >
                      <Avatar
                        :image="$user(row.owner)?.user_image"
                        :label="$user(row.owner)?.full_name || 'Deleted'"
                        size="xs"
                      />
                      <span :title="row.owner">{{
                        $user(row.owner)?.full_name || 'Deleted'
                      }}</span>
                    </div>
                  </div>

                  <span :title="row.recentDate" class="w-28 text-end">{{
                    row.relativeModified
                  }}</span>
                </div>
              </div>
              <hr v-if="i !== files.length - 1" />
            </template>
          </div>
        </div>
      </div>
    </template>
  </div>
  <!-- <ContextMenu
      v-if="rowEvent && selectedRow"
      :key="selectedRow.name"
      :action-items="dropdownActionItems(selectedRow)"
      :event="rowEvent"
      :close="() => (rowEvent = false)"
    /> -->
</template>

<script setup lang="ts">
import { Avatar, TabButtons } from 'frappe-ui'
// import ContextMenu from '@/components/ContextMenu.vue'
import { useInfiniteScroll } from '@vueuse/core'
import LucideGrid from '~icons/lucide/grid'
import LucideList from '~icons/lucide/list'

const thumbnail = ref(
  JSON.parse(localStorage.getItem('writer-view') || '"list"'),
)
watch(thumbnail, (v) => localStorage.setItem('writer-view', JSON.stringify(v)))
const props = defineProps({
  groups: Object,
  resource: Object,
  actionItems: Array,
})

const container = useTemplateRef<HTMLElement>('container')
useInfiniteScroll(
  container,
  () => {
    if (props.resource.hasNextPage && !props.resource.loading) {
      props.resource.next()
    }
  },
  {
    distance: 10,
    canLoadMore: () => {
      return props.resource.hasNextPage
    },
  },
)
</script>
