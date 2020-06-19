<template>
  <div>
    <form class="ui form" @submit.prevent="submit">
      <div v-if="errors.length > 0" role="alert" class="ui negative message">
        <div class="header"><translate translate-context="Content/Admin/Error message.Title">Error while creating invitation</translate></div>
        <ul class="list">
          <li v-for="error in errors">{{ error }}</li>
        </ul>
      </div>
      <div class="inline fields">
        <div class="ui field">
          <label><translate translate-context="Content/*/Input.Label">Invitation code</translate></label>
          <input name="code" type="text" v-model="code" :placeholder="labels.placeholder" />
        </div>
        <div class="ui field">
          <button :class="['ui', {loading: isLoading}, 'button']" :disabled="isLoading" type="submit">
            <translate translate-context="Content/Admin/Button.Label/Verb">Get a new invitation</translate>
          </button>
        </div>
      </div>
    </form>
    <div v-if="invitations.length > 0">
      <div class="ui hidden divider"></div>
      <table class="ui ui basic table">
        <thead>
          <tr>
            <th><translate translate-context="Content/Admin/Table.Label/Noun">Code</translate></th>
            <th><translate translate-context="Content/Admin/Table.Label/Noun">Share link</translate></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="invitation in invitations" :key="invitation.code">
            <td>{{ invitation.code.toUpperCase() }}</td>
            <td><a :href="getUrl(invitation.code)" target="_blank">{{ getUrl(invitation.code) }}</a></td>
          </tr>
        </tbody>
      </table>
      <button class="ui basic button" @click="invitations = []"><translate translate-context="Content/Library/Button.Label">Clear</translate></button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data () {
    return {
      isLoading: false,
      code: null,
      invitations: [],
      errors: []
    }
  },
  computed: {
    labels () {
      return {
        placeholder: this.$pgettext('Content/Admin/Input.Placeholder', 'Leave empty for a random code')
      }
    }
  },
  methods: {
    submit () {
      let self = this
      this.isLoading = true
      this.errors = []
      let url = 'manage/users/invitations/'
      let payload = {
        code: this.code
      }
      axios.post(url, payload).then((response) => {
        self.isLoading = false
        self.invitations.unshift(response.data)
      }, (error) => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    getUrl (code) {
      return this.$store.getters['instance/absoluteUrl'](this.$router.resolve({name: 'signup', query: {invitation: code.toUpperCase()}}).href)
    }
  }
}
</script>
