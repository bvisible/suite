import { expect, test } from "../../fixtures/test";
import {
	createWriterDocument,
	openWriterDocument,
	shareWriterDocument,
	uniqueWriterTitle,
	writerEditor,
} from "../../helpers/writer";

test("reader cannot edit and editor can edit", async ({
	owner,
	collaborator,
	run,
}) => {
	const file = await createWriterDocument(
		owner.page.request,
		uniqueWriterTitle(run.run_id, "acl"),
	);

	await shareWriterDocument(owner.page.request, file.name, {
		user: collaborator.user.user,
		read: true,
	});
	await openWriterDocument(collaborator.page, file.name);
	await expect(writerEditor(collaborator.page)).toHaveAttribute(
		"contenteditable",
		"false",
	);
	await expect(
		collaborator.page.getByRole("button", { name: "Document actions" }),
	).toBeVisible();

	await shareWriterDocument(owner.page.request, file.name, {
		user: collaborator.user.user,
		read: true,
		write: true,
		comment: true,
	});
	await collaborator.page.reload();
	await expect(writerEditor(collaborator.page)).toHaveAttribute(
		"contenteditable",
		"true",
	);
});

test("a public document is readable but not editable by a guest", async ({
	owner,
	guestPage,
	run,
}) => {
	const file = await createWriterDocument(
		owner.page.request,
		uniqueWriterTitle(run.run_id, "public"),
	);
	await shareWriterDocument(owner.page.request, file.name, { read: true });

	await openWriterDocument(guestPage, file.name);
	await expect(writerEditor(guestPage)).toHaveAttribute("contenteditable", "false");
	await expect(guestPage.getByRole("button", { name: "Sign In" })).toBeVisible();
	await expect(guestPage.getByRole("button", { name: "Document actions" })).toHaveCount(0);
});
