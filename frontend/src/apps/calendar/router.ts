import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: { name: 'Month' },
  },
  {
    path: '/month',
    name: 'Month',
    component: () => import('@/pages/CalendarView.vue'),
  },
  {
    path: '/week',
    name: 'Week',
    component: () => import('@/pages/CalendarView.vue'),
  },
  {
    path: '/day',
    name: 'Day',
    component: () => import('@/pages/CalendarView.vue'),
  },
]

const router = createRouter({ history: createWebHistory('/calendar'), routes })

// router.beforeEach(async (to, _, next) => {
//   if (document.referrer.includes("/app/setup-wizard"))
//     window.location.replace("/app");

//   const { isLoggedIn } = sessionStore();
//   if (!isLoggedIn) return to.meta.isLogin ? next() : next({ name: "Login" });

//   const { userResource, mailboxes } = userStore();
//   await userResource.promise;
//   await mailboxes.promise;
//   const user = userResource.data;
//   const mailboxRoute = {
//     name: "Mailbox",
//     params: { mailbox: mailboxes.data?.[0]?.id },
//   };

//   if (user.is_mail_admin) {
//     if (!user.tenant) return to.meta.isSetup ? next() : next({ name: "Setup" });
//     if (!user.is_mail_user && !to.meta.isDashboard)
//       return next({ name: "Domains" });
//   } else if (to.meta.isDashboard) return next(mailboxRoute);

//   if (["/", "/mailbox", "/mailbox/"].includes(to.path))
//     return next(mailboxRoute);

//   return to.meta.isLogin || to.meta.isSetup ? next(mailboxRoute) : next();
// });

export default router
