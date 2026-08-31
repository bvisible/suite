import { expect, test } from "../../fixtures/test";
import { createFolder, driveEntities } from "../../helpers/drive";

function uniqueName(runId: string, label: string): string {
	return `${label}-${runId}-${Date.now()}`;
}

// "New › Spreadsheet" / "New › Presentation" create a native content doc in the
// folder the user is looking at, hand off to that app's editor, and leave a
// backing Drive File behind (the content-app model Writer already uses). We
// create inside a fresh folder so the backing File is the only entity there.

test("New › Spreadsheet creates a sheet in the current folder and opens Sheets", async ({
	owner,
	run,
}) => {
	await owner.page.goto("/drive");
	const folder = await createFolder(owner.page, uniqueName(run.run_id, "sheets"));
	await owner.page.goto(`/drive/d/${folder.name}`);
	// Let the folder view (and the installed-apps list that gates the menu item)
	// settle so the Create menu doesn't re-render mid-click.
	await owner.page.waitForLoadState("networkidle");

	await owner.page.getByRole("button", { name: "Create", exact: true }).click();
	const item = owner.page.getByRole("menuitem", { name: "Spreadsheet", exact: true });
	await expect(item).toBeVisible();
	await item.click();

	await expect(owner.page).toHaveURL(/\/sheets\/[^/]+/);

	await expect
		.poll(async () => (await driveEntities(owner.page.request, folder.name)).length)
		.toBe(1);
});

test("New › Presentation hands off from Drive into Slides", async ({ owner }) => {
	// Routing-only (mirrors the Writer "creating from Drive routes into Writer"
	// check): the Slides editor owns deck creation, so we assert the hand-off
	// rather than racing its heavier boot for the backing File.
	await owner.page.goto("/drive/presentations");
	await owner.page.locator("#create-button").click();
	await expect(owner.page).toHaveURL(/\/slides\/presentation\//);
});
