<template>
	<div class="min-h-screen bg-gray-50 p-4">
		<div class="max-w-7xl mx-auto space-y-8">
			<!-- Header with Navigation -->
			<div class="flex justify-between items-center py-6">
				<div class="text-center flex-1">
					<h1 class="text-4xl font-bold text-gray-900 mb-2">Sae Video Conferencing</h1>
					<p class="text-lg text-gray-600">
						Connect, collaborate, and communicate seamlessly
					</p>
				</div>
			</div>

			<!-- Main content -->
			<div class="grid grid-cols-1 lg:grid-cols-7 gap-12 items-start">
				<!-- Left side - Video preview -->
				<div class="lg:col-span-4">
					<VideoPreview />
				</div>

				<!-- Right side - Join meeting form -->
				<div class="lg:col-span-3">
					<JoinMeetingForm />
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import JoinMeetingForm from "@/components/JoinMeetingForm.vue";
import VideoPreview from "@/components/VideoPreview.vue";
</script>
