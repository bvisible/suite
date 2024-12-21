<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-100 items-center">
		<!-- Navbar -->
		<div
			class="z-10 w-full flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-300"
		>
			<div class="flex items-center gap-2">
				<img src="../icons/slides.svg" class="h-7" />
				<div class="select-none font-semibold">Slides</div>
			</div>
		</div>

		<!-- Presentation Cards -->
		<div class="w-[80%] h-full my-8 flex flex-col gap-4">
			<div class="font-semibold text-gray-600 px-4">Presentations</div>
			<div class="grid grid-cols-5 gap-4 h-[95%] overflow-y-auto p-4">
				<div
					v-for="presentation in presentationList.data"
					:key="presentation.name"
					:style="{
						backgroundImage: `url(${presentation.slides[0].thumbnail})`,
						backgroundSize: 'cover',
						backgroundPosition: 'center',
					}"
					class="w-[200px] h-[112.5px] rounded-lg shadow-2xl cursor-pointer"
				></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})
</script>
