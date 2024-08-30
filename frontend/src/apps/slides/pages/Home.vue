<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-50">
		<div class="flex justify-between bg-white p-2 shadow-xl shadow-gray-200 items-center">
			<div class="flex items-center gap-2">
				<Logo />
				<div class="font-semibold">Slides</div>
			</div>

			<div class="flex justify-between">
				<Button variant="solid" label="Present" size="sm">
					<template #prefix>
						<SlideshowIcon class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>

		<div class="flex h-full items-center justify-center">
			<!-- slide dimensions: 16:9 ratio -->
			<div class="h-[540px] w-[960px] bg-white drop-shadow-lg"></div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Logo from '@/icons/Logo.vue'
import SlideshowIcon from '@/icons/SlideshowIcon.vue'
</script>
