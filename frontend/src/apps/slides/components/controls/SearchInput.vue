<template>
	<TextInput v-model="model" type="text" :placeholder>
		<template #prefix>
			<LucideSearch class="size-4 text-ink-gray-5" />
		</template>
	</TextInput>
</template>

<script setup lang="ts">
import { TextInput } from 'frappe-ui'

const model = defineModel<string>({ required: true })

defineProps<{ placeholder?: string }>()
</script>
