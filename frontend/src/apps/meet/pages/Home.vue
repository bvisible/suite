<template>
	<div class="min-h-screen bg-gray-50 p-4">
		<div class="max-w-7xl mx-auto space-y-20">
			<!-- Header with Navigation -->
			<div class="flex gap-3 items-center py-6">
				<FrappeMeetingLogo />
				<h1 class="text-xl font-semibold text-gray-900">Frappe Meet</h1>
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
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";
</script>
