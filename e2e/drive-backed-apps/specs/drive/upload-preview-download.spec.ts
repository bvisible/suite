import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "../../fixtures/test";
import { waitForDriveEntity } from "../../helpers/drive";

const uploadFixture = resolve(__dirname, "fixtures/drive-upload.txt");
const fixtureContent = readFileSync(uploadFixture, "utf8").trim();

test("uploads, previews, and downloads a text file", async ({ owner, run }) => {
	const fileName = `preview-${run.run_id}-${Date.now()}.txt`;
	await owner.page.goto("/drive");
	await Promise.all([
		owner.page.waitForResponse(
			(response) => response.url().includes("upload_file") && response.ok(),
		),
		owner.page.getByTestId("drive-file-input").setInputFiles({
			name: fileName,
			mimeType: "text/plain",
			buffer: readFileSync(uploadFixture),
		}),
	]);
	const file = await waitForDriveEntity(owner.page.request, fileName);

	await owner.page.getByTestId(`drive-entity-${file.name}`).click();
	await expect(owner.page).toHaveURL(new RegExp(`/drive/f/${file.name}`));
	await expect(owner.page.locator("pre")).toHaveText(fixtureContent);

	await owner.page.getByRole("button", { name: "Entity actions" }).click();
	const downloadPromise = owner.page.waitForEvent("download");
	await owner.page.getByRole("menuitem", { name: "Download" }).click();
	const download = await downloadPromise;
	expect(download.suggestedFilename()).toBe(fileName);
	const downloadedPath = await download.path();
	expect(downloadedPath).not.toBeNull();
	expect(readFileSync(downloadedPath as string, "utf8").trim()).toBe(
		fixtureContent,
	);
});
