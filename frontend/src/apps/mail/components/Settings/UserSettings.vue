<template>
	<h1 class="font-semibold">{{ __('Profile') }}</h1>

	<div class="flex w-full items-center">
		<Avatar
			:image="user.data?.user_image"
			:label="user.data?.full_name"
			size="3xl"
			class="h-16 w-16"
		/>
		<div class="mx-4 flex flex-col">
			<span class="text-xl font-semibold">{{ user.data?.full_name }}</span>
			<span class="text-base text-gray-700">{{ user.data?.email }}</span>
		</div>
		<Button :label="__('Edit Photo')" class="ml-auto" @click="showEditPhoto = true" />
	</div>
	<FormControl type="data" :label="__('First Name')" />
	<FormControl type="data" :label="__('Last Name')" />
	<Button :label="__('Save Changes')" variant="solid" :disabled="true" />
	<Button :label="__('Change Password')" @click="showChangePassword = true" />

	<EditPhotoModal v-model="showEditPhoto" />
	<ChangePasswordModal v-model="showChangePassword" />
</template>
<script setup lang="ts">
import { inject, ref } from 'vue'
import { Avatar, Button, FormControl } from 'frappe-ui'

import ChangePasswordModal from '@/components/Modals/ChangePasswordModal.vue'
import EditPhotoModal from '@/components/Modals/EditPhotoModal.vue'

const user = inject('$user')

const showEditPhoto = ref(false)
const showChangePassword = ref(false)
</script>
