<template>
	<div class="m-3 flex flex-row items-center justify-center">
		<Card title="Login to Frappe Meet" class="w-full max-w-md mt-4">
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
			<div v-if="oAuthProviders.data?.length" class="mt-6 border-t text-center">
				<div class="-translate-y-1/2 transform">
					<span
						class="relative bg-surface-white px-2 text-sm font-medium leading-8 text-ink-gray-8"
					>
						or
					</span>
				</div>
			</div>
			<Button
				v-for="provider in oAuthProviders.data"
				:key="provider.name"
				class="mb-2 w-full"
				:link="provider.auth_url"
			>
				<div class="flex items-center">
					<div v-html="provider.icon" />
					<span class="ml-2">
						Continue with
						{{ provider.provider_name }}
					</span>
				</div>
			</Button>
		</Card>
	</div>
</template>

<script lang="ts" setup>
import { Button, Card, Input, createResource, toast } from "frappe-ui";
import { useRouter } from "vue-router";
import { session } from "../data/session";

const router = useRouter();

const oAuthProviders = createResource({
	url: "sae.api.account.oauth_providers",
	auto: true,
});

function submit(e) {
	const formData = new FormData(e.target);
	session.login.submit(
		{
			email: formData.get("email"),
			password: formData.get("password"),
		},
		{
			onSuccess: () => {
				router.push({
					name: "Home",
				});
			},
			onError: (error) => {
				toast.error(`Login failed: ${error.message}`);
			},
		},
	);
}
</script>
