import { toast, useCall } from "frappe-ui";
import { computed } from "vue";
import { useRouter } from "vue-router";

import { useConnectionState } from "./useConnectionState";
import { submit } from "../utils/request";

type MeetingType = "open" | "restricted";

export const useStartMeeting = () => {
	const router = useRouter();
	const connectionState = useConnectionState();
	const createMeeting = useCall<string, { meeting_type: MeetingType }>({
		url: "/api/v2/method/suite.meet.api.meeting.create",
		method: "POST",
		immediate: false,
	});

	const copyMeetingLink = (meetingCode: string) => {
		const path = router.resolve({
			name: "meet-meeting",
			params: { meetingId: meetingCode },
		}).href;
		navigator.clipboard.writeText(new URL(path, window.location.origin).href);
	};

	const startMeeting = async (meetingType: MeetingType) => {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		const creatingToastId = toast.loading(__("Creating meeting..."));
		let meetingCode: string;
		try {
			meetingCode = await submit(createMeeting, { meeting_type: meetingType });
		} catch (error) {
			toast.dismiss(creatingToastId);
			console.error("Error creating meeting:", error);
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			toast.error(__("Failed to create meeting. Please try again."));
			return;
		}

		toast.dismiss(creatingToastId);
		connectionState.justCreated = true;
		try {
			await router.push({
				name: "meet-meeting",
				params: { meetingId: meetingCode },
			});
		} catch (error) {
			console.error("Error opening meeting:", error);
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			toast.error(__("Meeting created, but could not open it."), {
				duration: 8000,
				action: {
					// //// Neoffice — i18n: text a person reads goes through __() (#1316)
					label: __("Copy link"),
					onClick: () => copyMeetingLink(meetingCode),
				},
			});
			return;
		}

		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.success(__("Meeting created successfully!"), {
			duration: 8000,
			action: {
				// //// Neoffice — i18n: text a person reads goes through __() (#1316)
				label: __("Copy link"),
				onClick: () => copyMeetingLink(meetingCode),
			},
		});
	};

	return {
		isStartingMeeting: computed(() => createMeeting.loading),
		startMeeting,
	};
};
