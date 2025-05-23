import { createRouter, createWebHistory } from 'vue-router'

import { sessionStore } from '@/stores/session'
import { userStore } from '@/stores/user'

const routes = [
	{
		path: '/signup',
		name: 'SignUp',
		component: () => import('@/pages/SignupView.vue'),
		meta: { isLogin: true },
	},
	{
		path: '/signup/personal',
		name: 'PersonalSignUp',
		component: () => import('@/pages/SignupView.vue'),
		meta: { isLogin: true },
	},
	{
		path: '/signup/business',
		name: 'BusinessSignUp',
		component: () => import('@/pages/BusinessSignupView.vue'),
		meta: { isLogin: true },
	},
	{
		path: '/signup/business/:requestKey',
		name: 'BusinessSetup',
		component: () => import('@/pages/BusinessSignupView.vue'),
		props: true,
		meta: { isLogin: true },
	},
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/LoginView.vue'),
		meta: { isLogin: true },
	},
	{
		path: '/reset-password',
		name: 'ForgotPassword',
		component: () => import('@/pages/ForgotPasswordView.vue'),
		meta: { isLogin: true },
	},
	{
		path: '/reset-password/:requestKey',
		name: 'ResetPassword',
		component: () => import('@/pages/ResetPasswordView.vue'),
		props: true,
		meta: { isLogin: true },
	},
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/pages/SetupView.vue'),
		meta: { isSetup: true },
	},
	{
		path: '/mailbox/:mailbox',
		name: 'Mailbox',
		component: () => import('@/pages/MailFolderView.vue'),
		props: true,
	},
	{
		path: '/mailbox/:mailbox/:threadID',
		name: 'Mail',
		component: () => import('@/pages/MailFolderView.vue'),
		props: true,
	},
	{
		path: '/mime-message/incoming-mail/:id',
		name: 'IncomingMailMimeMessage',
		component: () => import('@/pages/MimeMessageView.vue'),
		props: true,
		meta: { isMimeMessage: true },
	},
	{
		path: '/mime-message/outgoing-mail/:id',
		name: 'OutgoingMailMimeMessage',
		component: () => import('@/pages/MimeMessageView.vue'),
		props: true,
		meta: { isMimeMessage: true },
	},
	{
		path: '/dashboard',
		redirect: { name: 'Domains' },
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/domains',
		name: 'Domains',
		component: () => import('@/pages/dashboard/DomainsView.vue'),
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/domains/:domainName',
		name: 'Domain',
		component: () => import('@/pages/dashboard/DomainView.vue'),
		props: true,
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/members',
		name: 'Members',
		component: () => import('@/pages/dashboard/MembersView.vue'),
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/invites',
		name: 'Invites',
		component: () => import('@/pages/dashboard/MembersView.vue'),
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/aliases',
		name: 'Aliases',
		component: () => import('@/pages/dashboard/MailAliasesView.vue'),
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/groups',
		name: 'Groups',
		component: () => import('@/pages/dashboard/MailGroupsView.vue'),
		meta: { isDashboard: true },
	},
	{
		path: '/dashboard/groups/:groupName',
		name: 'Group',
		component: () => import('@/pages/dashboard/MailGroupView.vue'),
		props: true,
		meta: { isDashboard: true },
	},
]

const router = createRouter({ history: createWebHistory('/mail'), routes })

router.beforeEach(async (to, from, next) => {
	if (document.referrer.includes('/app/setup-wizard')) window.location.replace('/app')

	const { isLoggedIn } = sessionStore()
	if (!isLoggedIn) return next(to.meta.isLogin ? undefined : { name: 'Login' })

	const { userResource } = userStore()
	await userResource.promise
	const user = userResource.data
	const mailboxRoute = { name: 'Mailbox', params: { mailbox: user.mailboxes[0].role } }

	if (user.is_mail_admin) {
		if (!user.tenant) return next(to.meta.isSetup ? undefined : { name: 'Setup' })
		if (!user.default_outgoing && !to.meta.isDashboard) return next({ name: 'Domains' })
	} else if (to.meta.isDashboard) return next(mailboxRoute)

	if (to.path === '/' || to.path === '/mailbox') return next(mailboxRoute)

	next(to.meta.isLogin || to.meta.isSetup ? mailboxRoute : undefined)
})

export default router
