<template>
  <main class="main pusher" v-title="labels.changePassword">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2>{{ labels.changePassword }}</h2>
        <form v-if="!success" class="ui form" @submit.prevent="submit()">
          <div v-if="errors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Signup/Card.Title">Error while changing your password</translate></h4>
            <ul class="list">
              <li v-for="error in errors">{{ error }}</li>
            </ul>
          </div>
          <template v-if="token && uid">
            <div class="field">
              <label><translate translate-context="Content/Settings/Input.Label">New password</translate></label>
              <password-input v-model="newPassword" />
            </div>
            <router-link :to="{path: '/login'}">
              <translate translate-context="Content/Signup/Link">Back to login</translate>
            </router-link>
            <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'success', 'button']" type="submit">
              <translate translate-context="Content/Signup/Button.Label">Update your password</translate></button>
          </template>
          <template v-else>
            <p><translate translate-context="Content/Signup/Paragraph">If the email address provided in the previous step is valid and linked to a user account, you should receive an email with reset instructions in the next couple of minutes.</translate></p>
          </template>
        </form>
        <div v-else class="ui positive message">
          <h4 class="header"><translate translate-context="Content/Signup/Card.Title">Password updated successfully</translate></h4>
          <p><translate translate-context="Content/Signup/Card.Paragraph">Your password has been updated successfully.</translate></p>
          <router-link :to="{name: 'login'}">
            <translate translate-context="Content/Signup/Link/Verb">Proceed to login</translate>
          </router-link>
        </div>
      </div>
    </section>
  </main>
</template>

<script>
import axios from "axios"
import PasswordInput from "@/components/forms/PasswordInput"

export default {
  props: ["defaultToken", "defaultUid"],
  components: {
    PasswordInput
  },
  data() {
    return {
      newPassword: "",
      isLoading: false,
      errors: [],
      token: this.defaultToken,
      uid: this.defaultUid,
      success: false
    }
  },
  computed: {
    labels() {
      return {
        changePassword: this.$pgettext('*/Signup/Title', "Change your password")
      }
    }
  },
  methods: {
    submit() {
      let self = this
      self.isLoading = true
      self.errors = []
      let payload = {
        uid: this.uid,
        token: this.token,
        new_password1: this.newPassword,
        new_password2: this.newPassword
      }
      return axios.post("auth/password/reset/confirm/", payload).then(
        response => {
          self.isLoading = false
          self.success = true
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
