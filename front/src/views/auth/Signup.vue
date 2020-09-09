<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2><translate translate-context="Content/Signup/Title">Create a funkwhale account</translate></h2>
        <signup-form :default-invitation="defaultInvitation" :next="next"></signup-form>
      </div>
    </section>
  </main>
</template>

<script>

import SignupForm from "@/components/auth/SignupForm"

export default {
  props: {
    defaultInvitation: { type: String, required: false, default: null },
    next: { type: String, default: "/" }
  },
  components: {
    SignupForm
  },
  data() {
    return {
      username: "",
      email: "",
      password: "",
      isLoadingInstanceSetting: true,
      errors: [],
      isLoading: false,
      invitation: this.defaultInvitation
    }
  },
  computed: {
    labels() {
      let title = this.$pgettext("*/Signup/Title", "Sign Up")
      return {
        title
      }
    }
  },
}
</script>
