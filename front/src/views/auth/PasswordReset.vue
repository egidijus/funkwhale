<template>
  <main class="main pusher" v-title="labels.reset">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2><translate translate-context="*/Login/*/Verb">Reset your password</translate></h2>
        <form class="ui form" @submit.prevent="submit()">
          <div v-if="errors.length > 0" role="alert" class="ui negative message">
            <div class="header"><translate translate-context="Content/Signup/Card.Title">Error while asking for a password reset</translate></div>
            <ul class="list">
              <li v-for="error in errors">{{ error }}</li>
            </ul>
          </div>
          <p><translate translate-context="Content/Signup/Paragraph">Use this form to request a password reset. We will send an email to the given address with instructions to reset your password.</translate></p>
          <div class="field">
            <label><translate translate-context="Content/Signup/Input.Label">Account's email</translate></label>
            <input
              required
              ref="email"
              type="email"
              name="email"
              autofocus
              :placeholder="labels.placeholder"
              v-model="email">
          </div>
          <router-link :to="{path: '/login'}">
            <translate translate-context="Content/Signup/Link">Back to login</translate>
          </router-link>
          <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'success', 'button']" type="submit">
            <translate translate-context="Content/Signup/Button.Label/Verb">Ask for a password reset</translate></button>
        </form>
      </div>
    </section>
  </main>
</template>

<script>
import axios from "axios"

export default {
  props: ["defaultEmail"],
  data() {
    return {
      email: this.defaultEmail,
      isLoading: false,
      errors: []
    }
  },
  mounted() {
    this.$refs.email.focus()
  },
  computed: {
    labels() {
      let reset = this.$pgettext('*/Login/*/Verb', "Reset your password")
      let placeholder = this.$pgettext('Content/Signup/Input.Placeholder', "Enter the email address linked to your account"
      )
      return {
        reset,
        placeholder
      }
    }
  },
  methods: {
    submit() {
      let self = this
      self.isLoading = true
      self.errors = []
      let payload = {
        email: this.email
      }
      return axios.post("auth/password/reset/", payload).then(
        response => {
          self.isLoading = false
          self.$router.push({
            name: "auth.password-reset-confirm"
          })
        },
        error => {
          self.errors = error.backendErrors
          self.isLoading = false
        }
      )
    }
  }
}
</script>
