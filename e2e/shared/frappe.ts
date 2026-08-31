import type { APIResponse } from "@playwright/test";

interface FrappeResponse<T> {
	message?: T;
	data?: T;
}

export async function frappeData<T>(response: APIResponse): Promise<T> {
	if (!response.ok()) {
		throw new Error(
			`Frappe request failed with ${response.status()}: ${await response.text()}`,
		);
	}
	const body = (await response.json()) as FrappeResponse<T>;
	const data = body.message ?? body.data;
	if (data === undefined) throw new Error("Frappe response contained no data");
	return data;
}
