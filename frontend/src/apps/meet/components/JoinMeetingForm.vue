<template>
	<div class="space-y-4">
		<div class="text-center lg:text-left">
			<h1 class="text-lg text-gray-900">Join or Start a Meeting</h1>
		</div>

		<div class="space-y-4">
			<Card class="p-6">
				<form class="space-y-4" @submit.prevent="joinMeeting">
					<FormControl
						label="Meeting Code"
						class="m-0.5"
						v-model="meetingCode"
						placeholder="abcd-efgh-ijkl"
						size="md"
					/>
					<Button
						variant="solid"
						size="lg"
						class="w-full"
						:disabled="!isMeetingCodeValid(meetingCode)"
					>
						Join
					</Button>
				</form>
			</Card>

			<div class="text-center">
				<p class="text-gray-500 mb-4">Or</p>
				<Button variant="outline" size="lg" @click="startNewMeeting" class="w-full">
					<template #prefix>
						<lucide-plus class="mr-2" />
					</template>
					Start an instant meeting
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, Card, FormControl, createResource, toast } from "frappe-ui";
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const meetingCode = ref("");

const joinMeeting = () => {
	if (meetingCode.value.trim()) {
		router.push({
			name: "Meeting",
			params: { meetingId: meetingCode.value.trim() },
		});
	} else {
		toast.error("Please enter a valid meeting code.");
	}
};

const createMeeting = createResource({
	url: "sae.api.meeting.create",
	method: "POST",
	makeParams: () => ({
		meeting_code: meetingCode.value.trim(),
	}),
	onSuccess: (meeting_code) => {
		router.push({
			name: "Meeting",
			params: { meetingId: meeting_code },
		});
	},
	onError: (error) => {
		console.error("Error creating meeting:", error);
		// Handle error, e.g., show an error message
	},
});

const startNewMeeting = () => {
	console.log("Starting new meeting");
	toast.promise(createMeeting.submit(), {
		loading: "Joining meeting...",
		success: "Meeting joined successfully!",
		error: "Failed to join meeting. Please try again.",
	});
};

const isMeetingCodeValid = (code) => {
	// ensure code is of the form xxxx-xxxx-xxxx
	const regex = /^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$/;

	return regex.test(code);
};
</script>
