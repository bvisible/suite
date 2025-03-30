<template>
	<div class="bg-gray-100 w-full h-screen flex flex-col items-center justify-center gap-2">
		<div class="text-2xl font-semibold">Access Denied</div>
		<div class="text-base text-gray-700">You do not have permission to access this page.</div>
		<router-link to="/">
			<Button :variant="'solid'" size="md" label="Go back to Home" class="my-6" />
		</router-link>
	</div>
</template>
