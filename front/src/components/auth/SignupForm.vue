<template>
  <div v-if="submitted">
    <div class="ui success message">
      <p v-if="signupRequiresApproval">
        <translate translate-context="Content/Signup/Form/Paragraph">Your account request was successfully submitted. You will be notified by email when our moderation team has reviewed your request.</translate>
      </p>
      <p v-else>
        <translate translate-context="Content/Signup/Form/Paragraph">Your account was successfully created. Please verify your email before trying to login.</translate>
      </p>
    </div>
    <h2><translate translate-context="Content/Login/Title/Verb">Log in to your Funkwhale account</translate></h2>
    <login-form button-classes="basic green" :show-signup="false"></login-form>
  </div>
  <form
    v-else
    :class="['ui', {'loading': isLoadingInstanceSetting}, 'form']"
    @submit.prevent="submit()">
    <p class="ui message" v-if="!$store.state.instance.settings.users.registration_enabled.value">
      <translate translate-context="Content/Signup/Form/Paragraph">Public registrations are not possible on this instance. You will need an invitation code to sign up.</translate>
    </p>
    <p class="ui message" v-else-if="signupRequiresApproval">
      <translate translate-context="Content/Signup/Form/Paragraph">Registrations on this pod are open, but reviewed by moderators before approval.</translate>
    </p>
    <template v-if="formCustomization && formCustomization.help_text">
      <rendered-description :content="formCustomization.help_text" :fetch-html="fetchDescriptionHtml" :permissive="true"></rendered-description>
      <div class="ui hidden divider"></div>
    </template>
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <div class="header"><translate translate-context="Content/Signup/Form/Paragraph">Your account cannot be created.</translate></div>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="required field">
      <label><translate translate-context="Content/*/*">Username</translate></label>
      <input
      ref="username"
      name="username"
      required
      type="text"
      autofocus
      :placeholder="labels.usernamePlaceholder"
      v-model="username">
    </div>
    <div class="required field">
      <label><translate translate-context="Content/*/*/Noun">Email</translate></label>
      <input
      ref="email"
      name="email"
      required
      type="email"
      :placeholder="labels.emailPlaceholder"
      v-model="email">
    </div>
    <div class="required field">
      <label><translate translate-context="*/*/*">Password</translate></label>
      <password-input v-model="password" />
    </div>
    <div class="required field" v-if="!$store.state.instance.settings.users.registration_enabled.value">
      <label><translate translate-context="Content/*/Input.Label">Invitation code</translate></label>
      <input
      required
      type="text"
      name="invitation"
      :placeholder="labels.placeholder"
      v-model="invitation">
    </div>
    <template v-if="signupRequiresApproval && formCustomization && formCustomization.fields && formCustomization.fields.length > 0">
      <div :class="[{required: field.required}, 'field']" v-for="(field, idx) in formCustomization.fields" :key="idx">
        <label :for="`custom-field-${idx}`">{{ field.label }}</label>
        <textarea
          v-if="field.input_type === 'long_text'"
          :value="customFields[field.label]"
          :required="field.required"
          @input="$set(customFields, field.label, $event.target.value)" rows="5"></textarea>
        <input v-else type="text" :value="customFields[field.label]" :required="field.required" @input="$set(customFields, field.label, $event.target.value)">
      </div>
    </template>
    <button :class="['ui', buttonClasses, {'loading': isLoading}, ' right floated button']" type="submit">
      <translate translate-context="Content/Signup/Button.Label">Create my account</translate>
    </button>
  </form>
</template>

<script>
import axios from "axios"
import logger from "@/logging"

import LoginForm from "@/components/auth/LoginForm"
import PasswordInput from "@/components/forms/PasswordInput"

export default {
  props: {
    defaultInvitation: { type: String, required: false, default: null },
    next: { type: String, default: "/" },
    buttonClasses: { type: String, default: "green" },
    customization: { type: Object, default: null},
    fetchDescriptionHtml: { type: Boolean, default: false},
    fetchDescriptionHtml: { type: Boolean, default: false},
    signupApprovalEnabled: {type: Boolean, default: null, required: false},
  },
  components: {
    LoginForm,
    PasswordInput,
  },
  data() {
    return {
      username: "",
      email: "",
      password: "",
      isLoadingInstanceSetting: true,
      errors: [],
      isLoading: false,
      invitation: this.defaultInvitation,
      customFields: {},
      submitted: false,
    }
  },
  created() {
    let self = this
    this.$store.dispatch("instance/fetchSettings", {
      callback: function() {
        self.isLoadingInstanceSetting = false
      }
    })
  },
  computed: {
    labels() {
      let placeholder = this.$pgettext(
        "Content/Signup/Form/Placeholder",
        "Enter your invitation code (case insensitive)"
      )
      let usernamePlaceholder = this.$pgettext("Content/Signup/Form/Placeholder", "Enter your username")
      let emailPlaceholder = this.$pgettext("Content/Signup/Form/Placeholder", "Enter your email")
      return {
        usernamePlaceholder,
        emailPlaceholder,
        placeholder
      }
    },
    formCustomization () {
      return this.customization || this.$store.state.instance.settings.moderation.signup_form_customization.value
    },
    signupRequiresApproval () {
      if (this.signupApprovalEnabled === null) {
        return this.$store.state.instance.settings.moderation.signup_approval_enabled.value
      }
      return this.signupApprovalEnabled
    }
  },
  methods: {
    submit() {
      var self = this
      self.isLoading = true
      this.errors = []
      var payload = {
        username: this.username,
        password1: this.password,
        password2: this.password,
        email: this.email,
        invitation: this.invitation,
        request_fields: this.customFields,
      }
      return axios.post("auth/registration/", payload).then(
        response => {
          logger.default.info("Successfully created account")
          self.submitted = true
          self.isLoading = false
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

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
</style>
