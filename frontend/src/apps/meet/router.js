import { userResource } from "@/data/user";
import { createRouter, createWebHistory } from "vue-router";
import { session } from "./data/session";

const routes = [
	{
		path: "/",
		name: "Home",
		component: () => import("@/pages/Home.vue"),
	},
	{
		path: "/admin/sfu-dashboard",
		name: "SFUDashboard",
		component: () => import("@/pages/SFUDashboardPage.vue"),
		meta: { requiresAdmin: true },
	},
	{
		path: "/:meetingId",
		name: "Meeting",
		component: () => import("@/pages/Meeting.vue"),
	},
	{
		name: "Login",
		path: "/login",
		component: () => import("@/pages/Login.vue"),
	},
];

const router = createRouter({
	history: createWebHistory("/sae"),
	routes,
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn = session.isLoggedIn;
	let user = null;

	try {
		await userResource.promise;
		user = userResource.data;
	} catch (error) {
		isLoggedIn = false;
	}

	// Check if route requires admin access
	if (to.meta?.requiresAdmin && user) {
		const isAdmin =
			user.roles?.includes("System Manager") ||
			user.roles?.includes("Administrator");
		if (!isAdmin) {
			// Redirect non-admin users to home
			next({ name: "Home" });
			return;
		}
	}

	if (to.name === "Login" && isLoggedIn) {
		next({ name: "Home" });
	} else if (to.name !== "Login" && !isLoggedIn) {
		next({ name: "Login" });
	} else {
		next();
	}
});

export default router;
