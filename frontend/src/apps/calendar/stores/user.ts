import { defineStore } from "pinia";
import { createResource } from "frappe-ui";
import { useRouter } from "vue-router";

const router = useRouter();

export const userStore = defineStore("mail-users", () => {
  const userResource = createResource({
    url: "mail.api.account.get_user_info",
    onSuccess: (data) => {
      if (data?.is_mail_user) identities.fetch();
    },
    onError: (error) => {
      if (error && error.exc_type === "AuthenticationError")
        router.push("/login");
    },
    auto: true,
  });

  const identities = createResource({ url: "mail.api.account.get_identities" });

  return { userResource, identities };
});
