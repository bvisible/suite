import { expect, test } from "../fixtures/test";

test("private Drive and Writer routes require authentication", async ({
	guestPage,
}) => {
	await guestPage.goto("/drive");
	await expect(guestPage).toHaveURL(/\/login\?redirect-to=.*drive/);

	await guestPage.goto("/writer");
	await expect(guestPage).toHaveURL(/\/login\?redirect-to=.*writer/);
});
