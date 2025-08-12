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
				<div class="flex space-x-4">
					<router-link
						v-if="isAdmin"
						to="/admin/sfu-dashboard"
						class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
					>
						<svg
							class="w-4 h-4 mr-2"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							></path>
						</svg>
						SFU Dashboard
					</router-link>
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
