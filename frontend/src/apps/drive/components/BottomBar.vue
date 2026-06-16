<template>
  <div
    class="grid grid-cols-5 bg-surface-elevation-2 border-t border-outline-gray-2 standalone:pb-4"
    :style="{
      gridTemplateColumns: `repeat(${sidebarItems.length}, minmax(0, 1fr))`,
    }"
  >
    <button
      v-for="tab in sidebarItems"
      :key="tab.label"
      class="flex flex-col items-center justify-center transition active:scale-95 h-[50px]"
      @click="$router.push(tab.route)"
    >
      <component
        :is="tab.icon"
        class="size-6"
        :class="[tab.highlight() ? 'text-ink-gray-8' : 'text-ink-gray-5']"
      />
    </button>
  </div>
</template>
<script>
import LucideBuilding2 from '~icons/lucide/building-2'
import LucideClock from '~icons/lucide/clock'
import LucideHome from '~icons/lucide/home'
import LucideStar from '~icons/lucide/star'
import LucideUsers from '~icons/lucide/users'
import store from '@/apps/drive/store'

export default {
  name: 'Sidebar',
  emits: ['toggleMobileSidebar'],
  data() {
    return {
      sidebarResizing: false,
      store,
    }
  },
  computed: {
    isExpanded() {
      return store.state.sidebarCollapsed
    },
    team() {
      return this.$route.params.team || localStorage.getItem('recentTeam')
    },
    sidebarItems() {
      const first = store.state.breadcrumbs[0] || {}
      return [
        {
          label: 'Home',
          route: { name: 'drive-Home' },
          icon: LucideHome,
          highlight: () => {
            return first.name === 'drive-Home'
          },
        },
        {
          label: 'Team',
          route: { name: 'drive-Teams' },
          icon: LucideBuilding2,
          highlight: () => {
            return this.$route.name === 'drive-Teams'
          },
        },
        {
          label: 'Recents',
          route: { name: 'drive-Recents' },
          icon: LucideClock,
          highlight: () => {
            return first.name === 'drive-Recents'
          },
        },

        {
          label: 'Shared',
          route: { name: 'drive-Shared' },
          icon: LucideUsers,
          highlight: () => {
            return first.name === 'drive-Shared'
          },
        },
        {
          label: 'Favourites',
          route: { name: 'drive-Favourites' },
          icon: LucideStar,
          highlight: () => {
            return first.name === 'drive-Favourites'
          },
        },
      ]
    },
  },
  methods: {
    toggleExpanded() {
      return this.$store.commit('setSidebarCollapsed', this.isExpanded ? false : true)
    },
    startResize() {
      document.addEventListener('mousemove', this.resize)
      document.addEventListener('mouseup', () => {
        document.body.classList.remove('select-none')
        document.body.classList.remove('cursor-col-resize')
        this.sidebarResizing = false
        document.removeEventListener('mousemove', this.resize)
      })
    },
    resize(e) {
      this.sidebarResizing = true
      document.body.classList.add('select-none')
      document.body.classList.add('cursor-col-resize')
      let sidebarWidth = e.clientX
      const range = [60, 180]
      if (sidebarWidth > range[0] && sidebarWidth < range[1]) {
        sidebarWidth = 60
        store.commit('setSidebarCollapsed', false)
      }
      if (sidebarWidth > 180) {
        store.commit('setSidebarCollapsed', true)
      }
      /* if (sidebarWidth < 100) {
          this.$store.commit("setSidebarCollapsed", false )
        }
        if (sidebarWidth > 100) {
          this.$store.commit("setSidebarCollapsed", true )
        } */
    },
  },
}
</script>
