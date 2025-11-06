<script setup lang="ts"></script>

<template>
  <div class="flex flex-col h-screen">
    <router-view :key="$route.fullPath" v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </div>
</template>

<style scoped></style>
