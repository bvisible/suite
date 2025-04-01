<template>
	<form class="flex flex-col space-y-4" @submit.prevent="signup.submit">
		<FormControl
			v-model="user.first_name"
			type="text"
			:label="__('First Name')"
			placeholder="John"
			autocomplete="given-name"
			class="w-full"
			required
		/>
		<FormControl
			v-model="user.last_name"
			type="text"
			:label="__('Last Name')"
			placeholder="Doe"
			autocomplete="family-name"
			class="w-full"
		/>
		<div class="flex items-center justify-between">
			<FormControl
				v-model="user.username"
				type="text"
				:label="__('Username')"
				placeholder="johndoe"
				autocomplete="username"
				class="w-full"
				required
			/>
			<FeatherIcon class="mx-2.5 mb-1.5 mt-auto h-4 w-4 text-gray-400" name="at-sign" />
			<FormControl
				v-if="personalSignupDomains?.data?.length"
				v-model="user.domain"
				:type="personalSignupDomains?.data?.length === 1 ? 'text' : 'select'"
				:readonly="personalSignupDomains?.data?.length === 1"
				:options="personalSignupDomains?.data"
				:label="__('Domain Name')"
				class="w-full"
				required
			/>
		</div>
		<FormControl
			v-model="user.email"
			type="email"
			:label="__('Backup Email')"
			placeholder="johndoe@personal.com"
			autocomplete="email"
			class="w-full"
			required
		/>
		<FormControl
			v-model="user.password"
			type="password"
			:label="__('Password')"
			placeholder="*********"
			autocomplete="new-password"
			class="w-full"
			required
		/>
		<ErrorMessage :message="signup.error" />
		<Button variant="solid" :label="__('Sign Up')" :loading="signup.loading" />
	</form>
	<div class="mt-6 text-center">
		<router-link class="text-center text-base font-medium hover:underline" to="/login">
			{{ __('Already have an account? Log in.') }}
		</router-link>
	</div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, FeatherIcon, FormControl, createResource } from 'frappe-ui'

import { sessionStore } from '@/stores/session'

const router = useRouter()
const { login } = sessionStore()

const user = reactive({
	first_name: '',
	last_name: '',
	username: '',
	domain: '',
	email: '',
	password: '',
})

const signupSettings = createResource({
	url: 'mail.api.get_signup_settings',
	auto: true,
	cache: 'signupSettings',
	onSuccess: (data) => {
		if (!Number(data.allow_personal_signup)) router.push('/signup/business')
	},
})

const personalSignupDomains = createResource({
	url: 'mail.api.get_personal_signup_domains',
	auto: true,
	cache: 'personalSignupDomains',
	onSuccess: (data) => {
		if (data.length === 1) user.domain = data[0]
	},
})

const signup = createResource({
	url: 'mail.api.account.personal_signup',
	makeParams: () => ({ ...user }),
	onSuccess: () => login.submit({ usr: `${user.username}@${user.domain}`, pwd: user.password }),
})
</script>
