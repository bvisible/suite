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

			<!-- Quick Stats for Non-Admin Users -->
			<div v-if="!isAdmin" class="mt-12">
				<h2 class="text-2xl font-bold text-gray-900 mb-6">System Status</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<div class="bg-white p-6 rounded-lg shadow">
						<div class="flex items-center">
							<div
								class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mr-3"
							>
								<svg
									class="w-4 h-4 text-white"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									></path>
								</svg>
							</div>
							<div>
								<p class="text-sm font-medium text-gray-600">SFU Status</p>
								<p class="text-lg font-semibold text-gray-900">Connected</p>
							</div>
						</div>
					</div>

					<div class="bg-white p-6 rounded-lg shadow">
						<div class="flex items-center">
							<div
								class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center mr-3"
							>
								<svg
									class="w-4 h-4 text-white"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"
									></path>
								</svg>
							</div>
							<div>
								<p class="text-sm font-medium text-gray-600">Active Meetings</p>
								<p class="text-lg font-semibold text-gray-900">
									{{ activeMeetingsCount }}
								</p>
							</div>
						</div>
					</div>

					<div class="bg-white p-6 rounded-lg shadow">
						<div class="flex items-center">
							<div
								class="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center mr-3"
							>
								<svg
									class="w-4 h-4 text-white"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path
										fill-rule="evenodd"
										d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
										clip-rule="evenodd"
									></path>
								</svg>
							</div>
							<div>
								<p class="text-sm font-medium text-gray-600">Server Load</p>
								<p class="text-lg font-semibold text-gray-900">Normal</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import JoinMeetingForm from "@/components/JoinMeetingForm.vue";
import VideoPreview from "@/components/VideoPreview.vue";
import { userResource } from "@/data/user";
import { computed, onMounted, ref } from "vue";

const activeMeetingsCount = ref(0);

const isAdmin = computed(() => {
	const user = userResource.data;
	return (
		user?.roles?.includes("System Manager") ||
		user?.roles?.includes("Administrator") ||
		false
	);
});

onMounted(async () => {
	// Load basic stats for non-admin users
	if (!isAdmin.value) {
		try {
			// Simulate API call to get basic stats
			activeMeetingsCount.value = Math.floor(Math.random() * 10);
		} catch (error) {
			console.error("Failed to load basic stats:", error);
		}
	}
});
</script>
