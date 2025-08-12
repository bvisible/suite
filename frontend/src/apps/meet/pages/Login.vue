<template>
	<div class="m-3 flex flex-row items-center justify-center">
		<Card title="Login to Sae" class="w-full max-w-md mt-4">
			<form class="flex flex-col space-y-2 w-full px-1" @submit.prevent="submit">
				<Input
					required
					name="email"
					type="text"
					placeholder="johndoe@email.com"
					label="User ID"
				/>
				<Input
					required
					name="password"
					type="password"
					placeholder="••••••"
					label="Password"
				/>
				<Button :loading="session.login.loading" variant="solid">Login</Button>
			</form>
		</Card>
	</div>
</template>

<script lang="ts" setup>
import { Button, Card, Input, toast } from "frappe-ui";
import { useRouter } from "vue-router";
import { session } from "../data/session";

const router = useRouter();

function submit(e) {
	const formData = new FormData(e.target);
	session.login
		.submit({
			email: formData.get("email"),
			password: formData.get("password"),
		})
		.then(() => {
			router.push("/");
		})
		.catch((error) => {
			toast.error("Login failed");
		});
}
</script>
