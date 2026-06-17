import { computed, reactive } from "vue";
import { useSessionStore } from "@/boot/session";
import { userResource } from "./user";

/**
 * Meet session adapter.
 *
 * The standalone Meet app owned a bespoke session object (login/logout +
 * cookie-derived current user). In the suite, "who is logged in" is the shared
 * `useSessionStore` (src/boot/session.ts). This adapter delegates auth state to
 * the shared store while preserving the `session.user.{sessionUser,full_name,
 * avatar,...}` shape that meet components/composables read, sourced from meet's
 * own `userResource` (kept for role checks + profile fields).
 *
 * `useSessionStore()` requires an active Pinia, which main.ts installs before
 * mount, so it is safe to call lazily from the getters below.
 */
export const session = reactive({
	user: computed(() => {
		const store = useSessionStore();
		return {
			sessionUser: store.user,
			...userResource.data,
		};
	}),
	isLoggedIn: computed(() => useSessionStore().isLoggedIn),
});
