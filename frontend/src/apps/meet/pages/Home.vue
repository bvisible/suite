<template>
	<div class="flex h-screen bg-surface-base" data-testid="home-page">
		<!-- //// Neoffice — the shared NeoCockpit chrome replaces Meet's own sidebar so
		     every Suite app carries the same left rail as the rest of Neoffice. It
		     falls back to <MeetSidebar /> by itself when the chrome cannot mount. //// -->
		<NeoCockpitSidebar />

		<div class="flex flex-1 flex-col overflow-auto">
			<div class="flex flex-1 items-start justify-center pt-[100px]">
				<div class="w-[760px] max-w-full px-6">
					<div class="mb-2 flex flex-col gap-0.5">
						<h1 class="text-lg-semibold text-ink-gray-8 tracking-[0.2px]">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ firstName ? __('Hey {0},', [firstName]) : __('Hey there,') }}
						</h1>
						<p class="text-sm text-ink-gray-6 tracking-[0.28px] leading-[1.5]">
							<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
							{{ __('Start an open meeting, create a restricted meeting, or join with a code.') }}
						</p>
					</div>

					<div class="mt-[42px] grid grid-cols-2 gap-4 md:grid-cols-4">
						<button
							class="group flex flex-1 flex-col items-center gap-2.5 rounded-8 border border-outline-gray-1 bg-surface-gray-1 p-1.5 transition-colors hover:bg-surface-gray-2"
							@click="startInstantMeeting"
						>
							<div class="flex h-[100px] w-full items-center justify-center rounded-[14px] border border-outline-gray-1 bg-surface-base">
								<div class="flex h-11 w-11 items-center justify-center rounded-[30px] bg-surface-base text-ink-gray-8 transition-transform group-hover:scale-105">
									<LucideZap class="size-6 text-ink-gray-8" />
								</div>
							</div>
							<!-- //// Neoffice — i18n: text a person reads goes through __(), and the label wraps to two lines where upstream cut it to one: French runs longer ("Programmer une réunion" read "Programmer une réuni…") (#1316) -->
							<span class="text-sm-medium w-full line-clamp-2 text-center text-ink-gray-8 tracking-[0.21px]">{{ __('Instant meet') }}</span>
						</button>

						<button
							class="group flex flex-1 flex-col items-center gap-2.5 rounded-8 border border-outline-gray-1 bg-surface-gray-1 p-1.5 transition-colors hover:bg-surface-gray-2"
							@click="startRestrictedMeeting"
						>
							<div class="flex h-[100px] w-full items-center justify-center rounded-[14px] border border-outline-gray-1 bg-surface-base">
								<div class="flex h-11 w-11 items-center justify-center rounded-[30px] bg-surface-base text-ink-gray-8 transition-transform group-hover:scale-105">
									<LucideLock class="size-6 text-ink-gray-8" />
								</div>
							</div>
							<!-- //// Neoffice — i18n: text a person reads goes through __(), and the label wraps to two lines where upstream cut it to one: French runs longer ("Programmer une réunion" read "Programmer une réuni…") (#1316) -->
							<span class="text-sm-medium w-full line-clamp-2 text-center text-ink-gray-8 tracking-[0.21px]">{{ __('Restricted meet') }}</span>
						</button>

						<button
							class="group flex flex-1 flex-col items-center gap-2.5 rounded-8 border border-outline-gray-1 bg-surface-gray-1 p-1.5 transition-colors hover:bg-surface-gray-2"
							@click="openScheduleDialog"
						>
							<div class="flex h-[100px] w-full items-center justify-center rounded-[14px] border border-outline-gray-1 bg-surface-base">
								<div class="flex h-11 w-11 items-center justify-center rounded-[30px] bg-surface-base text-ink-gray-8 transition-transform group-hover:scale-105">
									<LucideCalendarPlus class="size-6 text-ink-gray-8" />
								</div>
							</div>
							<!-- //// Neoffice — i18n: text a person reads goes through __(), and the label wraps to two lines where upstream cut it to one: French runs longer ("Programmer une réunion" read "Programmer une réuni…") (#1316) -->
							<span class="text-sm-medium w-full line-clamp-2 text-center text-ink-gray-8 tracking-[0.21px]">{{ __('Schedule meet') }}</span>
						</button>

						<button
							class="group flex flex-1 flex-col items-center gap-2.5 rounded-8 border border-outline-gray-1 bg-surface-gray-1 p-1.5 transition-colors hover:bg-surface-gray-2"
							@click="showJoinDialog = true"
						>
							<div class="flex h-[100px] w-full items-center justify-center rounded-[14px] border border-outline-gray-1 bg-surface-base">
								<div class="flex h-11 w-11 items-center justify-center rounded-[30px] bg-surface-base text-ink-gray-8 transition-transform group-hover:scale-105">
									<LucideLink class="size-6 text-ink-gray-8" />
								</div>
							</div>
							<!-- //// Neoffice — i18n: text a person reads goes through __(), and the label wraps to two lines where upstream cut it to one: French runs longer ("Programmer une réunion" read "Programmer une réuni…") (#1316) -->
							<span class="text-sm-medium w-full line-clamp-2 text-center text-ink-gray-8 tracking-[0.21px]">{{ __('Join with code') }}</span>
						</button>
					</div>

					<UpcomingMeetings ref="upcomingMeetingsRef" />
				</div>
			</div>
		</div>

		<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
		<Dialog
			v-model:open="showJoinDialog"
			:title="__('Join with meeting code')"
			dismissible
		>
			<template #default>
				<FormControl
					v-model="meetingCode"
					placeholder="abcd-efgh-ijkl"
					:error="meetingCodeError"
					@keydown.enter="joinWithCode"
					data-testid="meeting-code-input"
				/>
			</template>
			<template #actions>
				<div class="flex justify-end">
					<Button
						variant="solid"
						@click="joinWithCode"
						data-testid="join-meeting-button"
					>
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						{{ __('Join') }}
					</Button>
				</div>
			</template>
		</Dialog>

		<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
		<Dialog v-model:open="showScheduleDialog" :title="__('Schedule meet')" dismissible>
			<template #default>
				<div class="space-y-4">
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<FormControl v-model="scheduleTitle" :label="__('Title')" :placeholder="__('Team meeting')" />
					<div class="grid grid-cols-1 gap-3 md:grid-cols-3">
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						<!-- //// Neoffice — format `ll`, the date as the reader writes it (« 14 oct. 2026 »): upstream's "MMM D, YYYY" reads « oct. 14, 2026 » in French (#1321) -->
						<FormControl
							v-model="scheduleDate"
							:label="__('Date')"
							type="date"
							format="ll"
							:placeholder="__('Select date')"
						/>
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						<FormControl
							v-model="scheduleStartTime"
							:label="__('Start')"
							type="time"
							:interval="15"
							:format="timeInputFormat"
							:placeholder="__('Select time')"
						/>
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						<FormControl
							v-model="scheduleEndTime"
							:label="__('End')"
							type="time"
							:interval="15"
							:format="timeInputFormat"
							:placeholder="__('Select time')"
						/>
					</div>
					<ParticipantSelector
						v-model="scheduleParticipants"
						:account="calendarStore.accountId"
						:display-participants="scheduledParticipants"
						:excluded-emails="currentUserEmail ? [currentUserEmail] : []"
					/>
				</div>
			</template>
			<template #actions>
				<div class="flex justify-end">
					<Button
						variant="solid"
						:loading="scheduleMeeting.loading"
						:disabled="!isScheduleTimeValid"
						@click="submitScheduledMeeting"
					>
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						{{ __('Schedule') }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import {
	Button,
	Dialog,
	FormControl,
	toast,
	useCall,
} from "frappe-ui";
import { ref, computed, onMounted, onScopeDispose, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";

import { userStore as useCalendarUserStore } from "@/apps/calendar/stores/user";
import dayjs from "@/apps/calendar/utils/dayjs";
// //// Neoffice — the reader's clock in the time inputs (maintenance#1321).
import { usesMeridiem } from "@/neoffice/clock";
import ParticipantSelector from "@/apps/calendar/components/ParticipantSelector.vue";
import {
	adjustScheduleEndTime,
	adjustScheduleStartTime,
} from "@/apps/calendar/utils/scheduleTime";
import { useStartMeeting } from "../composables/useStartMeeting";
import { submit } from "../utils/request";
import { useRootStore } from "@/stores/root";
// //// Neoffice: NeoCockpit chrome (falls back to the native MeetSidebar itself) ////
import NeoCockpitSidebar from "../components/NeoCockpitSidebar.vue";
import UpcomingMeetings from "../components/UpcomingMeetings.vue";
import LucideCalendarPlus from "~icons/lucide/calendar-plus";
import LucideZap from "~icons/lucide/zap";
import LucideLink from "~icons/lucide/link";
import LucideLock from "~icons/lucide/lock";

interface CalendarParticipant {
	email: string;
	_name?: string;
	user_image?: string;
	participation_status?: string;
	expect_reply?: boolean;
	isNew?: boolean;
}

const router = useRouter();
//// Neoffice — `HH:mm` on a 24-hour locale; upstream wrote `h:mm A` for every reader (maintenance#1321).
const timeInputFormat = usesMeridiem(dayjs()) ? "h:mm A" : "HH:mm";
const root = useRootStore();
const { isStartingMeeting, startMeeting } = useStartMeeting();
const calendarStore = useCalendarUserStore();
const meetingCode = ref("");
const meetingCodeError = ref("");
const showJoinDialog = ref(false);
const showScheduleDialog = ref(false);
const scheduleTitle = ref("");
const scheduleDate = ref(dayjs().format("YYYY-MM-DD"));
const scheduleStartTime = ref(dayjs().add(1, "hour").startOf("hour").format("HH:mm"));
const scheduleEndTime = ref(dayjs().add(2, "hour").startOf("hour").format("HH:mm"));
const scheduleParticipants = ref<CalendarParticipant[]>([]);
const upcomingMeetingsRef = ref<{ reload: () => void } | null>(null);

watch(scheduleStartTime, (startTime) => {
	scheduleEndTime.value = adjustScheduleEndTime(startTime, scheduleEndTime.value);
});

watch(scheduleEndTime, (endTime) => {
	scheduleStartTime.value = adjustScheduleStartTime(scheduleStartTime.value, endTime);
});

const userResource = useCall<{ name?: string; full_name?: string; user_image?: string }>({
	url: "/api/v2/method/suite.api.account.get_logged_in_user",
});

const firstName = computed(() => {
	const name = userResource.data?.full_name || userResource.data?.name || "";
	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return name.split(" ")[0];
});

const scheduleStart = computed(() => dayjs(`${scheduleDate.value}T${scheduleStartTime.value}`));
const scheduleEnd = computed(() => dayjs(`${scheduleDate.value}T${scheduleEndTime.value}`));

const isScheduleTimeValid = computed(
	() =>
		Boolean(scheduleDate.value && scheduleStartTime.value && scheduleEndTime.value) &&
		scheduleStart.value.isValid() &&
		scheduleEnd.value.isValid() &&
		scheduleEnd.value.isAfter(scheduleStart.value),
);

const scheduledDuration = computed(() => {
	if (!isScheduleTimeValid.value) return "";
	const start = scheduleStart.value;
	const end = scheduleEnd.value;
	const diff = dayjs.duration(end.diff(start));
	return dayjs.duration({ hours: Math.floor(diff.asHours()), minutes: diff.minutes() }).toISOString();
});

const currentUserEmail = computed(() => calendarStore.userResource.data?.name || userResource.data?.name);

const scheduledParticipants = computed(() => {
	const currentName = calendarStore.userResource.data?.full_name || userResource.data?.full_name;
	const currentImage = calendarStore.userResource.data?.user_image || userResource.data?.user_image;
	const participants: CalendarParticipant[] = currentUserEmail.value
		? [
				{
					email: currentUserEmail.value,
					_name: currentName,
					user_image: currentImage,
					participation_status: "ACCEPTED",
				},
			]
		: [];

	participants.push(...scheduleParticipants.value);

	return participants;
});

const scheduleMeeting = useCall({
	url: "/api/v2/method/suite.meet.api.schedule.create_scheduled_meeting",
	method: "POST",
	params: () => ({
		account: calendarStore.accountId,
		title: scheduleTitle.value,
		start: scheduleStart.value.format("YYYY-MM-DD[T]HH:mm:ss"),
		duration: scheduledDuration.value,
		time_zone: dayjs.tz?.guess?.() || Intl.DateTimeFormat().resolvedOptions().timeZone,
		participants: scheduledParticipants.value,
		send_scheduling_messages: scheduledParticipants.value.length > 1,
	}),
	immediate: false,
	onSuccess: () => {
		showScheduleDialog.value = false;
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.success(__("Meeting scheduled."));
		upcomingMeetingsRef.value?.reload();
	},
	onError: (error: unknown) => {
		console.error("Error scheduling meeting:", error);
	},
});

const startInstantMeeting = () => startMeeting("open");

const startRestrictedMeeting = () => startMeeting("restricted");

const openScheduleDialog = async () => {
	try {
		await calendarStore.userResource.promise;
		if (!calendarStore.accountId) {
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			toast.error(__("Set up Calendar before scheduling a Meet."));
			return;
		}
		showScheduleDialog.value = true;
	} catch (error) {
		console.error("Failed to load calendar account:", error);
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.error(__("Could not load Calendar account."));
	}
};

const submitScheduledMeeting = () => {
	if (!calendarStore.accountId) {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.error(__("Set up Calendar before scheduling a Meet."));
		return;
	}
	if (!isScheduleTimeValid.value) {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.error(__("Enter a valid date and an end time after the start time."));
		return;
	}
	toast.promise(submit(scheduleMeeting), {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		loading: __("Scheduling meeting..."),
		error: __("Failed to schedule meeting. Please try again."),
	});
};

const joinWithCode = () => {
	meetingCodeError.value = "";

	if (!meetingCode.value.trim()) {
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		meetingCodeError.value = __("Please enter a meeting code");
		return;
	}

	if (!isMeetingCodeValid(meetingCode.value.trim())) {
		meetingCodeError.value =
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			__("Please enter a valid meeting code (format: xxxx-xxxx-xxxx)");
		return;
	}

	showJoinDialog.value = false;
	router.push({
		name: "meet-meeting",
		params: { meetingId: meetingCode.value.trim() },
	});
};

const isMeetingCodeValid = (code: string) => {
	const regex = /^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$/;
	return regex.test(code);
};

const unregisterPaletteGroups = root.registerPaletteGroups("meet-home", () => [
	{
		commands: [
			{
				id: "meet-start-open",
				label: "Start instant meet",
				enterHint: "start instant meet",
				icon: "lucide-zap",
				keywords: ["new", "instant", "room"],
				disabled: isStartingMeeting.value,
				run: startInstantMeeting,
			},
			{
				id: "meet-start-restricted",
				label: "Start restricted meet",
				enterHint: "start restricted meet",
				icon: "lucide-lock",
				keywords: ["new", "private", "room"],
				disabled: isStartingMeeting.value,
				run: startRestrictedMeeting,
			},
			{
				id: "meet-join-code",
				label: "Join with code",
				enterHint: "join with code",
				icon: "lucide-link",
				keywords: ["room", "call"],
				run: () => (showJoinDialog.value = true),
			},
			{
				id: "meet-schedule",
				label: "Schedule meet",
				enterHint: "schedule meet",
				icon: "lucide-calendar-plus",
				keywords: ["calendar", "new"],
				run: openScheduleDialog,
			},
		],
	},
]);
onScopeDispose(unregisterPaletteGroups);

onMounted(() => {
	document.documentElement.style.overflow = "hidden";
});
onUnmounted(() => {
	document.documentElement.style.overflow = "";
});

</script>
