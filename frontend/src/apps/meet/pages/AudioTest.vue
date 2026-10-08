<!-- Vibe coded file meant only for testing audio notifications -->

<template>
	<div class="min-h-screen bg-gray-50 flex items-center justify-center p-8">
		<div class="max-w-2xl mx-auto">
			<div class="bg-white rounded-6 shadow-lg p-8">
				<div class="text-center mb-8">
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<h1 class="text-4xl-bold text-gray-900 mb-2">{{ __('Audio Notification Test') }}</h1>
					<p class="text-gray-600">{{ __('Test and tune the meeting notification sounds') }}</p>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					<!-- Join Notification -->
					<div class="bg-green-50 border border-green-200 rounded-6 p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-plus class="w-5 h-5 text-green-600" />
							</div>
							<div>
								<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
								<h3 class="font-semibold text-green-900">{{ __('User Joined') }}</h3>
								<p class="text-sm text-green-700">{{ __('Someone joins the meeting') }}</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="green"
							class="w-full"
							@click="playJoinNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play Join Sound') }}
						</Button>
						<div class="mt-3 text-xs text-green-600">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							<strong>{{ __('Current:') }}</strong> C4 → G4 → E5 → C5 {{ __('({0}s, {1}% volume)', [0.5, 20]) }}
						</div>
					</div>

					<!-- Leave Notification -->
					<div class="bg-red-50 border border-red-200 rounded-6 p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-minus class="w-5 h-5 text-red-600" />
							</div>
							<div>
								<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
								<h3 class="font-semibold text-red-900">{{ __('User Left') }}</h3>
								<p class="text-sm text-red-700">{{ __('Someone leaves the meeting') }}</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="red"
							class="w-full"
							@click="playLeaveNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play Leave Sound') }}
						</Button>
						<div class="mt-3 text-xs text-red-600">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							<strong>{{ __('Current:') }}</strong> G4 → E4 → C4 {{ __('({0}s, {1}% volume)', [0.4, 20]) }}
						</div>
					</div>

					<!-- Join Request Notification -->
					<div class="bg-blue-50 border border-blue-200 rounded-6 p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-check class="w-5 h-5 text-blue-600" />
							</div>
							<div>
								<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
								<h3 class="font-semibold text-blue-900">{{ __('Join Request') }}</h3>
								<p class="text-sm text-blue-700">{{ __('Someone requests to join') }}</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="blue"
							class="w-full"
							@click="playJoinRequestNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play Request Sound') }}
						</Button>
						<div class="mt-3 text-xs text-blue-600">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							<strong>{{ __('Current:') }}</strong> F4 → A4 → F4 → C5 {{ __('({0}s, {1}% volume)', [0.6, 25]) }}
						</div>
					</div>

					<!-- Chat Notification -->
					<div class="bg-purple-50 border border-purple-200 rounded-6 p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3">
								<lucide-message-circle class="w-5 h-5 text-purple-600" />
							</div>
							<div>
								<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
								<h3 class="font-semibold text-purple-900">{{ __('Chat Message') }}</h3>
								<p class="text-sm text-purple-700">{{ __('New chat message received') }}</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="purple"
							class="w-full"
							@click="playChatNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play Chat Sound') }}
						</Button>
						<div class="mt-3 text-xs text-purple-600">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							<strong>{{ __('Current:') }}</strong> E4 → G4 {{ __('({0}s, {1}% volume)', [0.25, 20]) }}
						</div>
					</div>

					<!-- Hand Raise Notification -->
					<div class="bg-orange-50 border border-orange-200 rounded-6 p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-3">
								<lucide-hand class="w-5 h-5 text-orange-600" />
							</div>
							<div>
								<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
								<h3 class="font-semibold text-orange-900">{{ __('Hand Raised') }}</h3>
								<p class="text-sm text-orange-700">{{ __('Someone raises their hand') }}</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="amber"
							class="w-full"
							@click="playRaiseHandNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play Hand Raise Sound') }}
						</Button>
						<div class="mt-3 text-xs text-orange-600">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							<strong>{{ __('Current:') }}</strong> C5 → E5 → G5 {{ __('({0}s, {1}% volume)', [0.5, 20]) }}
						</div>
					</div>
				</div>

				<!-- Test All Button -->
				<div class="mt-8 pt-6 border-t border-gray-200">
					<div class="text-center">
						<Button
							variant="outline"
							size="lg"
							@click="playAllNotifications"
							:disabled="isPlaying"
							class="mb-4"
						>
							<template #prefix>
								<lucide-play-circle class="w-5 h-5" />
							</template>
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Play All Notifications (Sequential)') }}
						</Button>
						<p class="text-sm text-gray-500">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Test all sounds in sequence with 1-second delays') }}
						</p>
					</div>
				</div>

				<!-- Instructions -->
				<div class="mt-6 p-4 bg-gray-50 rounded-6">
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<h4 class="font-semibold text-gray-900 mb-2">{{ __('Testing Tips:') }}</h4>
					<ul class="text-sm text-gray-600 space-y-1">
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						<li>• {{ __('Click individual buttons to test each notification') }}</li>
						<li>• {{ __('Use "Play All" to compare sounds in sequence') }}</li>
						<li>• {{ __('Edit frequencies/timing in') }} <code class="bg-gray-200 px-1 rounded-4">audioNotifications.ts</code></li>
						<li>• {{ __('Refresh page after code changes to test updates') }}</li>
						<li>• {{ __('Check browser console for any AudioContext errors') }}</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";
import { ref } from "vue";
import audioNotificationManager from "../utils/audioNotifications";

const isPlaying = ref(false);

// Play individual notifications
const playJoinNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playJoinNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playLeaveNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playLeaveNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playJoinRequestNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playJoinRequestNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playChatNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playChatNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playRaiseHandNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playRaiseHandNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

// Play all notifications in sequence
const playAllNotifications = async () => {
	isPlaying.value = true;

	try {
		await audioNotificationManager.playJoinNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playLeaveNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playJoinRequestNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playChatNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playRaiseHandNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};
</script>
