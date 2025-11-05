<script setup lang="ts"></script>

<template>
  <router-view :key="$route.fullPath" v-slot="{ Component }">
    <component :is="Component" />
  </router-view>
</template>

<style scoped></style>
