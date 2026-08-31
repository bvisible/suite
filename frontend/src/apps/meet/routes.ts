import type { RouteRecordRaw } from "vue-router";

// Install the meet-local navigation guard (requiresAdmin role check) on the
// shared suite router. Imported for side effects only.
import "@/apps/meet/router";

// Boot side-effects the suite's shared main.ts does not run, so trigger them
// on meet module load.
import { loadMediaPreferences } from "@/apps/meet/data/mediaPreferences";
import { installConsoleBuffer } from "@/apps/meet/utils/diagnostics/consoleBuffer";

loadMediaPreferences();
installConsoleBuffer();

/**
 * Meet route module — mounted by the suite router under the '/meet' prefix.
 * Paths are RELATIVE to '/meet' (no leading slash; the empty-path child '' is
 * the app index). Route names are namespaced `meet-*` to avoid collisions in the
 * single suite router.
 *
 * All routes nest under MeetLayout, which sets up the socket connection,
 * provides the meet-local `$platform`, and wraps views in FrappeUIProvider +
 * Dialogs.
 *
 * `meet-meeting` is marked `meta.allowGuest` so the suite's auth guard lets
 * guests join meetings. The meet-local guard (./router.ts) enforces
 * `requiresAdmin` for audio-test.
 */
export const routes: RouteRecordRaw[] = [
	{
		path: "",
		component: () => import("@/apps/meet/pages/MeetLayout.vue"),
		children: [
			{
				path: "",
				name: "meet-home",
				component: () => import("@/apps/meet/pages/Home.vue"),
			},
			{
				path: "audio-test",
				name: "meet-audio-test",
				component: () => import("@/apps/meet/pages/AudioTest.vue"),
				meta: { requiresAdmin: true },
			},
			{
				path: ":meetingId",
				name: "meet-meeting",
				component: () => import("@/apps/meet/pages/Meeting.vue"),
				meta: { allowGuest: true },
			},
		],
	},
];

export default routes;
