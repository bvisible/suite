import { expect, test } from "../../fixtures/test";
import {
	createWriterDocument,
	openWriterDocument,
	uniqueWriterTitle,
	writerEditor,
} from "../../helpers/writer";

test("creates a document from Writer and lists it", async ({ owner }) => {
	await owner.page.goto("/writer");
	await owner.page.getByRole("button", { name: "New" }).click();
	await expect(owner.page).toHaveURL(/\/writer\/w\/([^/]+)(?:\/|$)/);
	const id = new URL(owner.page.url()).pathname.split("/")[3];
	await expect(writerEditor(owner.page)).toBeVisible();

	await owner.page.goto("/writer");
	await expect(owner.page.getByTestId(`writer-document-${id}`)).toBeVisible();
});

test("manual save survives a reload", async ({ owner, run }) => {
	const title = uniqueWriterTitle(run.run_id, "persistence");
	const file = await createWriterDocument(owner.page.request, title);
	const content = `Persisted content ${run.run_id} ${Date.now()}`;

	await openWriterDocument(owner.page, file.name);
	const editor = writerEditor(owner.page);
	await expect(editor).toHaveAttribute("contenteditable", "true");
	await editor.fill(content);
	await owner.page.keyboard.press("ControlOrMeta+s");
	await expect(owner.page.getByText("Saved document", { exact: true })).toBeVisible();

	await owner.page.reload();
	await expect(writerEditor(owner.page)).toBeVisible();
	await expect(writerEditor(owner.page)).toContainText(content);
});

test("Writer home lists API-created Drive documents", async ({ owner, run }) => {
	const title = uniqueWriterTitle(run.run_id, "listing");
	const file = await createWriterDocument(owner.page.request, title);

	await owner.page.goto("/writer");
	const row = owner.page.getByTestId(`writer-document-${file.name}`);
	await expect(row).toBeVisible();
	await expect(row).toContainText(title);
});
