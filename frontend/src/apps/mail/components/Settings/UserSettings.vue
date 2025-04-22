<template>
	<h1 class="mb-8 font-semibold">{{ __('Profile') }}</h1>
	<div class="flex w-full items-center justify-start gap-x-4">
		<Avatar
			:image="user.data?.user_image"
			:label="user.data?.full_name"
			size="3xl"
			class="h-20 w-20"
		/>
		<div class="flex flex-col">
			<span class="text-xl font-semibold">{{ user.data?.full_name }}</span>
			<span class="text-base text-gray-700">{{ user.data?.email }}</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import { inject } from 'vue'
import { Avatar } from 'frappe-ui'

const user = inject('$user')
</script>
