import {
	expect,
	test as base,
	type Browser,
	type BrowserContext,
	type Page,
} from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Credentials } from "../../shared/auth";

const statePath = resolve(__dirname, "../.state/run.json");
const userStatePath = (index: number) =>
	resolve(__dirname, `../.state/user-${index}.json`);

interface ProvisionedUser extends Credentials {
	user: string;
	drive_settings: string;
	user_folder: string;
}

interface ProvisionedRun {
	run_id: string;
	users: ProvisionedUser[];
}

interface AuthenticatedPage {
	context: BrowserContext;
	page: Page;
	user: ProvisionedUser;
}

interface Fixtures {
	owner: AuthenticatedPage;
	collaborator: AuthenticatedPage;
	guestPage: Page;
}

interface WorkerFixtures {
	run: ProvisionedRun;
}

async function authenticatedPage(
	browser: Browser,
	user: ProvisionedUser,
	storageState: string,
): Promise<AuthenticatedPage> {
	const context = await browser.newContext({ storageState });
	return { context, page: await context.newPage(), user };
}

export const test = base.extend<Fixtures, WorkerFixtures>({
	run: [
		async ({}, use) => {
			const run = JSON.parse(readFileSync(statePath, "utf8")) as ProvisionedRun;
			await use(run);
		},
		{ scope: "worker" },
	],
	owner: async ({ browser, run }, use, workerInfo) => {
		const userIndex = workerInfo.parallelIndex * 2;
		const authenticated = await authenticatedPage(
			browser,
			run.users[userIndex],
			userStatePath(userIndex),
		);
		await use(authenticated);
		await authenticated.context.close();
	},
	collaborator: async ({ browser, run }, use, workerInfo) => {
		const userIndex = workerInfo.parallelIndex * 2 + 1;
		const authenticated = await authenticatedPage(
			browser,
			run.users[userIndex],
			userStatePath(userIndex),
		);
		await use(authenticated);
		await authenticated.context.close();
	},
	guestPage: async ({ browser }, use) => {
		const context = await browser.newContext();
		const page = await context.newPage();
		await use(page);
		await context.close();
	},
});

export { expect };
