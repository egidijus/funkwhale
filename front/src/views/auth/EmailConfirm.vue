<template>
  <main class="main pusher" v-title="labels.confirm">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2>{{ labels.confirm }}</h2>
        <form v-if="!success" class="ui form" @submit.prevent="submit()">
          <div v-if="errors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Signup/Paragraph">Could not confirm your e-mail address</translate></h4>
            <ul class="list">
              <li v-for="error in errors">{{ error }}</li>
            </ul>
          </div>
          <div class="field">
            <label><translate translate-context="Content/Signup/Form.Label">Confirmation code</translate></label>
            <input name="confirmation-code" type="text" required v-model="key" />
          </div>
          <router-link :to="{path: '/login'}">
            <translate translate-context="Content/Signup/Link/Verb">Return to login</translate>
          </router-link>
          <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'success', 'button']" type="submit">
            {{ labels.confirm }}</button>
        </form>
        <div v-else class="ui positive message">
          <h4 class="header"><translate translate-context="Content/Signup/Message">E-mail address confirmed</translate></h4>
          <p><translate translate-context="Content/Signup/Paragraph">You can now use the service without limitations.</translate></p>
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

export default {
  props: ["defaultKey"],
  data() {
    return {
      isLoading: false,
      errors: [],
      key: this.defaultKey,
      success: false
    }
  },
  computed: {
    labels() {
      return {
        confirm: this.$pgettext('Head/Signup/Title', "Confirm your e-mail address")
      }
    }
  },
  methods: {
    submit() {
      let self = this
      self.isLoading = true
      self.errors = []
      let payload = {
        key: this.key
      }
      return axios.post("auth/registration/verify-email/", payload).then(
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
