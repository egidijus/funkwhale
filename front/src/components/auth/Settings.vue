<template>
  <main class="main pusher" v-title="labels.title">
    <div class="ui vertical stripe segment">
      <section class="ui text container">
        <h2 class="ui header">
          <translate translate-context="Content/Settings/Title">Account settings</translate>
        </h2>
        <form class="ui form" @submit.prevent="submitSettings()">
          <div v-if="settings.success" class="ui positive message">
            <h4 class="header">
              <translate translate-context="Content/Settings/Message">Settings updated</translate>
            </h4>
          </div>
          <div v-if="settings.errors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Settings/Error message.Title">Your settings can't be updated</translate></h4>
            <ul class="list">
              <li v-for="error in settings.errors">{{ error }}</li>
            </ul>
          </div>
          <div class="field" v-for="f in orderedSettingsFields">
            <label :for="f.id">{{ sharedLabels.fields[f.id].label }}</label>
            <p v-if="f.help">{{ sharedLabels.fields[f.id].help }}</p>
            <select :id="f.id" v-if="f.type === 'dropdown'" class="ui dropdown" v-model="f.value">
              <option :value="c" v-for="c in f.choices">{{ sharedLabels.fields[f.id].choices[c] }}</option>
            </select>
            <content-form :field-id="f.id" v-if="f.type === 'content'" v-model="f.value.text"></content-form>
          </div>
          <button :class="['ui', {'loading': isLoading}, 'button']" type="submit">
            <translate translate-context="Content/Settings/Button.Label/Verb">Update settings</translate>
          </button>
        </form>
      </section>
      <section class="ui text container">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <translate translate-context="Content/Settings/Title">Avatar</translate>
        </h2>
        <div class="ui form">
          <div v-if="avatarErrors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Settings/Error message.Title">Your avatar cannot be saved</translate></h4>
            <ul class="list">
              <li v-for="error in avatarErrors">{{ error }}</li>
            </ul>
          </div>
          {{ }}
          <attachment-input
            :value="avatar.uuid"
            @input="submitAvatar($event)"
            :initial-value="initialAvatar"
            :required="false"
            @delete="avatar = {uuid: null}">
            <translate translate-context="Content/Channel/*" slot="label">Avatar</translate>
            </attachment-input>
        </div>
      </section>

      <section class="ui text container">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <translate translate-context="Content/Settings/Title/Verb">Change my password</translate>
        </h2>
        <div class="ui message">
          <translate translate-context="Content/Settings/Paragraph'">Changing your password will also change your Subsonic API password if you have requested one.</translate>&nbsp;<translate translate-context="Content/Settings/Paragraph">You will have to update your password on your clients that use this password.</translate>
        </div>
        <form class="ui form" @submit.prevent="submitPassword()">
          <div v-if="passwordError" role="alert" class="ui negative message">
            <h4 class="header">
              <translate translate-context="Content/Settings/Error message.Title">Your password cannot be changed</translate>
            </h4>
            <ul class="list">
              <li v-if="passwordError == 'invalid_credentials'"><translate translate-context="Content/Settings/Error message.List item/Call to action">Please double-check your password is correct</translate></li>
            </ul>
          </div>
          <div class="field">
            <label for="old-password-field"><translate translate-context="Content/Settings/Input.Label">Old password</translate></label>
            <password-input field-id="old-password-field" required v-model="old_password" />
          </div>
          <div class="field">
            <label for="new-password-field"><translate translate-context="Content/Settings/Input.Label">New password</translate></label>
            <password-input field-id="new-password-field" required v-model="new_password" />
          </div>
          <dangerous-button
            :class="['ui', {'loading': isLoading}, 'warning', 'button']"
            :action="submitPassword">
            <translate translate-context="Content/Settings/Button.Label">Change password</translate>
            <p slot="modal-header"><translate translate-context="Popup/Settings/Title">Change your password?</translate></p>
            <div slot="modal-content">
              <p><translate translate-context="Popup/Settings/Paragraph">Changing your password will have the following consequences:</translate></p>
              <ul>
                <li><translate translate-context="Popup/Settings/List item">You will be logged out from this session and have to log in with the new one</translate></li>
                <li><translate translate-context="Popup/Settings/List item">Your Subsonic password will be changed to a new, random one, logging you out from devices that used the old Subsonic password</translate></li>
              </ul>
            </div>
            <div slot="modal-confirm"><translate translate-context="Popup/Settings/Button.Label">Disable access</translate></div>
          </dangerous-button>
        </form>
        <div class="ui hidden divider" />
        <subsonic-token-form />
      </section>

      <section class="ui text container" id="content-filters">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="eye slash outline icon"></i>
          <div class="content">
            <translate translate-context="Content/Settings/Title/Noun">Content filters</translate>
          </div>
        </h2>
        <p><translate translate-context="Content/Settings/Paragraph">Content filters help you hide content you don't want to see on the service.</translate></p>

        <button
          @click="$store.dispatch('moderation/fetchContentFilters')"
          class="ui icon button">
          <i class="refresh icon"></i>&nbsp;
          <translate translate-context="Content/*/Button.Label/Short, Verb">Refresh</translate>
        </button>
        <h3 class="ui header">
          <translate translate-context="Content/Settings/Title">Hidden artists</translate>
        </h3>
        <table class="ui compact very basic unstackable table">
          <thead>
            <tr>
              <th><translate translate-context="*/*/*/Noun">Name</translate></th>
              <th><translate translate-context="Content/*/*/Noun">Creation date</translate></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="filter in $store.getters['moderation/artistFilters']()" :key='filter.uuid'>
              <td>
                <router-link :to="{name: 'library.artists.detail', params: {id: filter.target.id }}">
                  {{ filter.target.name }}
                </router-link>
              </td>
              <td>
                <human-date :date="filter.creation_date"></human-date>
              </td>
              <td>
                <button @click="$store.dispatch('moderation/deleteContentFilter', filter.uuid)" class="ui basic tiny button">
                  <translate translate-context="*/*/*/Verb">Delete</translate>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
      <section class="ui text container" id="grants">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="open lock icon"></i>
          <div class="content">
            <translate translate-context="Content/Settings/Title/Noun">Authorized apps</translate>
          </div>
        </h2>
        <p><translate translate-context="Content/Settings/Paragraph">This is the list of applications that have access to your account data.</translate></p>
        <button
          @click="fetchApps()"
          class="ui icon button">
          <i class="refresh icon"></i>&nbsp;
          <translate translate-context="Content/*/Button.Label/Short, Verb">Refresh</translate>
        </button>
        <table v-if="apps.length > 0" class="ui compact very basic unstackable table">
          <thead>
            <tr>
              <th><translate translate-context="*/*/*/Noun">Application</translate></th>
              <th><translate translate-context="Content/*/*/Noun">Permissions</translate></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in apps" :key='app.client_id'>
              <td>
                {{ app.name }}
              </td>
              <td>
                {{ app.scopes }}
              </td>
              <td>
                <dangerous-button
                  class="ui tiny danger button"
                  @confirm="revokeApp(app.client_id)">
                  <translate translate-context="*/*/*/Verb">Revoke</translate>
                  <p slot="modal-header" v-translate="{application: app.name}" translate-context="Popup/Settings/Title">Revoke access for application "%{ application }"?</p>
                  <p slot="modal-content"><translate translate-context="Popup/Settings/Paragraph">This will prevent this application from accessing the service on your behalf.</translate></p>
                  <div slot="modal-confirm"><translate translate-context="*/Settings/Button.Label/Verb">Revoke access</translate></div>
                </dangerous-button>
              </td>
            </tr>
          </tbody>
        </table>
        <empty-state v-else>
          <translate slot="title" translate-context="Content/Applications/Paragraph">
            You don't have any application connected with your account.
          </translate>
          <translate translate-context="Content/Applications/Paragraph">
            If you authorize third-party applications to access your data, those applications will be listed here.
          </translate>
        </empty-state>
      </section>
      <section class="ui text container" id="apps">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="code icon"></i>
          <div class="content">
            <translate translate-context="Content/Settings/Title/Noun">Your applications</translate>
          </div>
        </h2>
        <p><translate translate-context="Content/Settings/Paragraph">This is the list of applications that you have created.</translate></p>
        <router-link class="ui success button" :to="{name: 'settings.applications.new'}">
          <translate translate-context="Content/Settings/Button.Label">Create a new application</translate>
        </router-link>
        <table v-if="ownedApps.length > 0" class="ui compact very basic unstackable table">
          <thead>
            <tr>
              <th><translate translate-context="*/*/*/Noun">Application</translate></th>
              <th><translate translate-context="Content/*/*/Noun">Scopes</translate></th>
              <th><translate translate-context="Content/*/*/Noun">Creation date</translate></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in ownedApps" :key='app.client_id'>
              <td>
                <router-link :to="{name: 'settings.applications.edit', params: {id: app.client_id}}">
                  {{ app.name }}
                </router-link>
              </td>
              <td>
                {{ app.scopes }}
              </td>
              <td>
                <human-date :date="app.created" />
              </td>
              <td>
                <router-link class="ui tiny success button" :to="{name: 'settings.applications.edit', params: {id: app.client_id}}">
                  <translate translate-context="Content/*/Button.Label/Verb">Edit</translate>
                </router-link>
                <dangerous-button
                  class="ui tiny danger button"
                  @confirm="deleteApp(app.client_id)">
                  <translate translate-context="*/*/*/Verb">Delete</translate>
                  <p slot="modal-header" v-translate="{application: app.name}" translate-context="Popup/Settings/Title">Delete application "%{ application }"?</p>
                  <p slot="modal-content"><translate translate-context="Popup/Settings/Paragraph">This will permanently delete the application and all the associated tokens.</translate></p>
                  <div slot="modal-confirm"><translate translate-context="*/Settings/Button.Label/Verb">Delete application</translate></div>
                </dangerous-button>
              </td>
            </tr>
          </tbody>
        </table>
        <empty-state v-else>
          <translate slot="title" translate-context="Content/Applications/Paragraph">
            You don't have any configured application yet.
          </translate>
          <translate translate-context="Content/Applications/Paragraph">
            Create one to integrate Funkwhale with third-party applications.
          </translate>
        </empty-state>
      </section>

      <section class="ui text container" id="plugins">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="code icon"></i>
          <div class="content">
            <translate translate-context="Content/Settings/Title/Noun">Plugins</translate>
          </div>
        </h2>
        <p><translate translate-context="Content/Settings/Paragraph">Use plugins to extend Funkwhale and get additional features.</translate></p>
        <router-link class="ui success button" :to="{name: 'settings.plugins'}">
          <translate translate-context="Content/Settings/Button.Label">Manage plugins</translate>
        </router-link>
      </section>
      <section class="ui text container">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="comment icon"></i>
          <div class="content">
            <translate translate-context="*/*/Button.Label">Change my email address</translate>
          </div>
        </h2>
        <p>
          <translate translate-context="Content/Settings/Paragraph'">Change the email address associated with your account. We will send a confirmation to the new address.</translate>
        </p>
        <p>
          <translate :translate-params="{email: $store.state.auth.profile.email}" translate-context="Content/Settings/Paragraph'">Your current email address is %{ email }.</translate>
        </p>
        <form class="ui form" @submit.prevent="changeEmail">
          <div v-if="changeEmailErrors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Settings/Error message.Title">We cannot change your email address</translate></h4>
            <ul class="list">
              <li v-for="error in changeEmailErrors">{{ error }}</li>
            </ul>
          </div>
          <div class="field">
            <label for="new-email"><translate translate-context="*/*/*">New email</translate></label>
            <input id="new-email" required v-model="newEmail" type="email" />
          </div>
          <div class="field">
            <label for="current-password-field-email"><translate translate-context="*/*/*">Password</translate></label>
            <password-input field-id="current-password-field-email" required v-model="emailPassword" />
          </div>
          <button type="submit" class="ui button"><translate translate-context="*/*/*">Update</translate></button>
        </form>
      </section>
      <section class="ui text container">
        <div class="ui hidden divider"></div>
        <h2 class="ui header">
          <i class="trash icon"></i>
          <div class="content">
            <translate translate-context="*/*/Button.Label">Delete my account</translate>
          </div>
        </h2>
        <p>
          <translate translate-context="Content/Settings/Paragraph'">You can permanently and irreversibly delete your account and all the associated data using the form below. You will be asked for confirmation.</translate>
        </p>
        <div role="alert" class="ui warning message">
          <translate translate-context="Content/Settings/Paragraph'">Your account will be deleted from our servers within a few minutes. We will also notify other servers who may have a copy of some of your data so they can proceed to deletion. Please note that some of these servers may be offline or unwilling to comply though.</translate>
        </div>
        <div class="ui form">
          <div v-if="accountDeleteErrors.length > 0" role="alert" class="ui negative message">
            <h4 class="header"><translate translate-context="Content/Settings/Error message.Title">We cannot delete your account</translate></h4>
            <ul class="list">
              <li v-for="error in accountDeleteErrors">{{ error }}</li>
            </ul>
          </div>
          <div class="field">
            <label for="current-password-field"><translate translate-context="*/*/*">Password</translate></label>
            <password-input field-id="current-password-field" required v-model="password" />
          </div>
          <dangerous-button
            :class="['ui', {'loading': isDeletingAccount}, {disabled: !password}, 'danger', 'button']"
            :action="deleteAccount">
            <translate translate-context="*/*/Button.Label">Delete my account…</translate>
            <p slot="modal-header"><translate translate-context="Popup/Settings/Title">Do you want to delete your account?</translate></p>
            <div slot="modal-content">
              <p><translate translate-context="Popup/Settings/Paragraph">This is irreversible and will permanently remove your data from our servers. You will we immediatly logged out.</translate></p>
            </div>
            <div slot="modal-confirm"><translate translate-context="*/*/Button.Label">Delete my account</translate></div>
          </dangerous-button>
        </div>
      </section>
    </div>
  </main>
</template>

<script>
import $ from "jquery"
import axios from "axios"
import logger from "@/logging"
import PasswordInput from "@/components/forms/PasswordInput"
import SubsonicTokenForm from "@/components/auth/SubsonicTokenForm"
import TranslationsMixin from "@/components/mixins/Translations"
import AttachmentInput from '@/components/common/AttachmentInput'

export default {
  mixins: [TranslationsMixin],
  components: {
    PasswordInput,
    SubsonicTokenForm,
    AttachmentInput
  },
  data() {
    let d = {
      // We need to initialize the component with any
      // properties that will be used in it
      old_password: "",
      new_password: "",
      avatar: {...(this.$store.state.auth.profile.avatar || {uuid: null})},
      passwordError: "",
      password: "",
      isLoading: false,
      isLoadingAvatar: false,
      isDeletingAccount: false,
      changeEmailErrors: [],
      isChangingEmail: false,
      newEmail: null,
      emailPassword: null,
      accountDeleteErrors: [],
      avatarErrors: [],
      apps: [],
      ownedApps: [],
      settings: {
        success: false,
        errors: [],
        order: ["summary", "privacy_level"],
        fields: {
          summary: {
            type: "content",
            initial: this.$store.state.auth.profile.summary || {text: '', content_type: 'text/markdown'},
          },
          privacy_level: {
            type: "dropdown",
            initial: this.$store.state.auth.profile.privacy_level,
            choices: ["me", "instance"]
          }
        }
      }
    }
    d.initialAvatar = d.avatar.uuid
    d.settings.order.forEach(id => {
      d.settings.fields[id].value = d.settings.fields[id].initial
      d.settings.fields[id].id = id
    })
    return d
  },
  created () {
    this.fetchApps()
    this.fetchOwnedApps()
  },
  mounted() {
    $("select.dropdown").dropdown()
  },
  methods: {
    submitSettings() {
      this.settings.success = false
      this.settings.errors = []
      let self = this
      let payload = this.settingsValues
      let url = `users/users/${this.$store.state.auth.username}/`
      return axios.patch(url, payload).then(
        response => {
          logger.default.info("Updated settings successfully")
          self.settings.success = true
          return axios.get("users/users/me/").then(response => {
            self.$store.dispatch("auth/updateProfile", response.data)
          })
        },
        error => {
          logger.default.error("Error while updating settings")
          self.isLoading = false
          self.settings.errors = error.backendErrors
        }
      )
    },
    fetchApps() {
      this.apps = []
      let self = this
      let url = `oauth/grants/`
      return axios.get(url).then(
        response => {
          self.apps = response.data
        },
        error => {
        }
      )
    },
    fetchOwnedApps() {
      this.ownedApps = []
      let self = this
      let url = `oauth/apps/`
      return axios.get(url).then(
        response => {
          self.ownedApps = response.data.results
        },
        error => {
        }
      )
    },
    revokeApp (id) {
      let self = this
      let url = `oauth/grants/${id}/`
      return axios.delete(url).then(
        response => {
          self.apps = self.apps.filter(a => {
            return a.client_id != id
          })
        },
        error => {
        }
      )
    },
    deleteApp (id) {
      let self = this
      let url = `oauth/apps/${id}/`
      return axios.delete(url).then(
        response => {
          self.ownedApps = self.ownedApps.filter(a => {
            return a.client_id != id
          })
        },
        error => {
        }
      )
    },
    submitAvatar(uuid) {
      this.isLoadingAvatar = true
      this.avatarErrors = []
      let self = this
      axios
        .patch(`users/users/${this.$store.state.auth.username}/`, {avatar: uuid})
        .then(
          response => {
            this.isLoadingAvatar = false
            self.avatar = response.data.avatar
            self.$store.commit("auth/avatar", response.data.avatar)
          },
          error => {
            self.isLoadingAvatar = false
            self.avatarErrors = error.backendErrors
          }
        )
    },
    submitPassword() {
      var self = this
      self.isLoading = true
      this.error = ""
      var credentials = {
        old_password: this.old_password,
        new_password1: this.new_password,
        new_password2: this.new_password
      }
      let url = "auth/registration/change-password/"
      return axios.post(url, credentials).then(
        response => {
          logger.default.info("Password successfully changed")
          self.$router.push({
            name: "profile.overview",
            params: {
              username: self.$store.state.auth.username
            }
          })
        },
        error => {
          if (error.response.status === 400) {
            self.passwordError = "invalid_credentials"
          } else {
            self.passwordError = "unknown_error"
          }
          self.isLoading = false
        }
      )
    },
    deleteAccount() {
      this.isDeletingAccount = true
      this.accountDeleteErrors = []
      let self = this
      let payload = {
        confirm: true,
        password: this.password,
      }
      axios.delete(`users/users/me/`, {data: payload})
        .then(
          response => {
            self.isDeletingAccount = false
            let msg = self.$pgettext('*/Auth/Message', 'Your deletion request was submitted, your account and content will be deleted shortly')
            self.$store.commit('ui/addMessage', {
              content: msg,
              date: new Date()
            })
            self.$store.dispatch('auth/logout')
          },
          error => {
            self.isDeletingAccount = false
            self.accountDeleteErrors = error.backendErrors
          }
        )
    },

    changeEmail() {
      this.isChangingEmail = true
      this.changeEmailErrors = []
      let self = this
      let payload = {
        password: this.emailPassword,
        email: this.newEmail,
      }
      axios.post(`users/users/change-email/`, payload)
        .then(
          response => {
            self.isChangingEmail = false
            self.newEmail = null
            self.emailPassword = null
            let msg = self.$pgettext('*/Auth/Message', 'Your email has been changed, please check your inbox for our confirmation message.')
            self.$store.commit('ui/addMessage', {
              content: msg,
              date: new Date()
            })
          },
          error => {
            self.isChangingEmail = false
            self.changeEmailErrors = error.backendErrors
          }
        )
    },
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/Settings/Title', "Account Settings")
      }
    },
    orderedSettingsFields() {
      let self = this
      return this.settings.order.map(id => {
        return self.settings.fields[id]
      })
    },
    settingsValues() {
      let self = this
      let s = {}
      this.settings.order.forEach(setting => {
        let conf = self.settings.fields[setting]
        s[setting] = conf.value
        if (setting === 'summary' && !conf.value.text) {
          s[setting] = null
        }
      })
      return s
    }
  }
}
</script>
