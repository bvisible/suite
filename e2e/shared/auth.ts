import type { APIRequestContext } from "@playwright/test";

export interface Credentials {
	email: string;
	password: string;
}

const admin: Credentials = {
	email: process.env.E2E_ADMIN_EMAIL ?? "Administrator",
	password: process.env.E2E_ADMIN_PASSWORD ?? "admin",
};

export async function loginViaApi(
	request: APIRequestContext,
	credentials: Credentials = admin,
): Promise<void> {
	const response = await request.post("/api/method/login", {
		form: { usr: credentials.email, pwd: credentials.password },
	});
	if (!response.ok()) {
		throw new Error(
			`Login failed for ${credentials.email} with status ${response.status()}`,
		);
	}
}
