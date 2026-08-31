import { expect, test } from "../../fixtures/test";
import {
	createWriterDocument,
	openWriterDocument,
	uniqueWriterTitle,
} from "../../helpers/writer";
import type { Locator, Page } from "@playwright/test";

// The editable last crumb is the only text-bearing button in the navbar — parent
// crumbs render as links and the other navbar buttons are icon-only.
function titleCrumb(page: Page): Locator {
	return page
		.locator("#navbar")
		.getByRole("button")
		.filter({ hasText: /\S/ })
		.first();
}

// While renaming, the inline field is the only <input> in the navbar.
function renameInput(page: Page): Locator {
	return page.locator("#navbar input");
}

test("renames a document from the breadcrumb and persists", async ({ owner, run }) => {
	const title = uniqueWriterTitle(run.run_id, "rename");
	const file = await createWriterDocument(owner.page.request, title);
	await openWriterDocument(owner.page, file.name);

	const crumb = titleCrumb(owner.page);
	await expect(crumb).toHaveText(title);

	await crumb.click();

	const input = renameInput(owner.page);
	await expect(input).toBeVisible();
	// Autofocuses with the current name pre-filled and selected.
	await expect(input).toBeFocused();
	await expect(input).toHaveValue(title);

	const newTitle = `${title} renamed`;
	await input.fill(newTitle);
	await input.press("Enter");

	await expect(input).toBeHidden();
	await expect(titleCrumb(owner.page)).toHaveText(newTitle);

	// Persisted server-side: survives a reload.
	await owner.page.reload();
	await expect(titleCrumb(owner.page)).toHaveText(newTitle);
});

test("keeps focus and selection when the breadcrumb rename opens", async ({ owner, run }) => {
	const title = uniqueWriterTitle(run.run_id, "focus");
	const file = await createWriterDocument(owner.page.request, title);
	await openWriterDocument(owner.page, file.name);

	await titleCrumb(owner.page).click();
	const input = renameInput(owner.page);

	// Regression: the field must stay focused (not blur-commit and exit) so the
	// selection stays visible for an immediate retype.
	await expect(input).toBeFocused();
	await expect(input).toBeVisible();
	await owner.page.waitForTimeout(400);
	await expect(input).toBeFocused();

	const selectionLength = await input.evaluate(
		(el: HTMLInputElement) => (el.selectionEnd ?? 0) - (el.selectionStart ?? 0),
	);
	expect(selectionLength).toBe(title.length);
});

test("Escape cancels the rename without changing the name", async ({ owner, run }) => {
	const title = uniqueWriterTitle(run.run_id, "cancel");
	const file = await createWriterDocument(owner.page.request, title);
	await openWriterDocument(owner.page, file.name);

	await titleCrumb(owner.page).click();
	const input = renameInput(owner.page);
	await expect(input).toBeVisible();

	await input.fill("Discarded name");
	await input.press("Escape");

	await expect(input).toBeHidden();
	await expect(titleCrumb(owner.page)).toHaveText(title);
});
