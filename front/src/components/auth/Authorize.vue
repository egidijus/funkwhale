<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <h2><i class="lock open icon"></i><translate translate-context="Content/Auth/Title/Verb">Authorize third-party app</translate></h2>
        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <h4 v-if="application" class="header"><translate translate-context="Popup/Moderation/Error message">Error while authorizing application</translate></h4>
          <h4 v-else class="header"><translate translate-context="Popup/Moderation/Error message">Error while fetching application data</translate></h4>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
        <div v-if="isLoading" class="ui inverted active dimmer">
          <div class="ui loader"></div>
        </div>
        <form v-else-if="application && !code" :class="['ui', {loading: isLoading}, 'form']" @submit.prevent="submit">
          <h3><translate translate-context="Content/Auth/Title" :translate-params="{app: application.name}">%{ app } wants to access your Funkwhale account</translate></h3>

          <h4 v-for="topic in topicScopes" class="ui header vertical-align">
            <span v-if="topic.write && !topic.read" :class="['ui', 'basic', 'right floated', 'tiny', 'vertically-spaced component-label label']">
              <i class="pencil icon"></i>
              <translate translate-context="Content/Auth/Label/Noun">Write-only</translate>
            </span>
            <span v-else-if="!topic.write && topic.read" :class="['ui', 'basic', 'right floated', 'tiny', 'vertically-spaced component-label label']">
              <translate translate-context="Content/Auth/Label/Noun">Read-only</translate>
            </span>
            <span v-else-if="topic.write && topic.read" :class="['ui', 'basic', 'right floated', 'tiny', 'vertically-spaced component-label label']">
              <i class="pencil icon"></i>
              <translate translate-context="Content/Auth/Label/Noun">Full access</translate>
            </span>
            <i :class="[topic.icon, 'icon']"></i>
            <div class="content">
              {{ topic.label }}
              <div class="sub header">
                {{ topic.description }}
              </div>
            </div>
          </h4>
          <div v-if="unknownRequestedScopes.length > 0">
            <p><strong><translate translate-context="Content/Auth/Paragraph">The application is also requesting the following unknown permissions:</translate></strong></p>
            <ul v-for="scope in unknownRequestedScopes">
              <li>{{ scope }}</li>
            </ul>

          </div>
          <button class="ui success labeled icon button" type="submit">
            <i class="lock open icon"></i>
            <translate translate-context="Content/Signup/Button.Label/Verb" :translate-params="{app: application.name}">Authorize %{ app }</translate>
          </button>
          <p v-if="redirectUri === 'urn:ietf:wg:oauth:2.0:oob'" key="1" v-translate translate-context="Content/Auth/Paragraph">
            You will be shown a code to copy-paste in the application.</p>
          <p v-else key="2" v-translate="{url: redirectUri}" translate-context="Content/Auth/Paragraph" :translate-params="{url: redirectUri}">You will be redirected to <strong>%{ url }</strong></p>

        </form>
        <div v-else-if="code">
          <p><strong><translate translate-context="Content/Auth/Paragraph">Copy-paste the following code in the application:</translate></strong></p>
          <copy-input :value="code"></copy-input>
        </div>
      </div>
    </section>
  </main>
</template>

<script>
import TranslationsMixin from "@/components/mixins/Translations"

import axios from 'axios'

import {checkRedirectToLogin} from '@/utils'
export default {
  mixins: [TranslationsMixin],
  props: [
    'clientId',
    'redirectUri',
    'scope',
    'responseType',
    'nonce',
    'state',
  ],
  data() {
    return {
      application: null,
      isLoading: false,
      errors: [],
      code: null,
      knownScopes: [
        {id: "profile", icon: 'user'},
        {id: "libraries", icon: 'book'},
        {id: "favorites", icon: 'heart'},
        {id: "listenings", icon: 'music'},
        {id: "follows", icon: 'users'},
        {id: "playlists", icon: 'list'},
        {id: "radios", icon: 'rss'},
        {id: "filters", icon: 'eye slash'},
        {id: "notifications", icon: 'bell'},
        {id: "edits", icon: 'pencil alternate'},
        {id: "security", icon: 'lock'},
        {id: "reports", icon: 'warning sign'},
      ]
    }
  },
  created () {
    checkRedirectToLogin(this.$store, this.$router)
    if (this.clientId) {
      this.fetchApplication()
    }
  },
  computed: {
    labels () {
      return {
        title: this.$pgettext('Head/Authorize/Title', "Allow application")
      }
    },
    requestedScopes () {
      return (this.scope || '').split(' ')
    },
    supportedScopes () {
      let supported = ['read', 'write']
      this.knownScopes.forEach(s => {
        supported.push(`read:${s.id}`)
        supported.push(`write:${s.id}`)
      })
      return supported
    },
    unknownRequestedScopes () {
      let self = this
      return this.requestedScopes.filter(s => {
        return self.supportedScopes.indexOf(s) < 0
      })
    },
    topicScopes () {
      let self = this
      let requested = this.requestedScopes
      let write = false
      let read = false
      if (requested.indexOf('read') > -1) {
        read = true
      }
      if (requested.indexOf('write') > -1) {
        write = true
      }

      return this.knownScopes.map(s => {
        let id = s.id
        return {
          id: id,
          icon: s.icon,
          label: self.sharedLabels.scopes[s.id].label,
          description: self.sharedLabels.scopes[s.id].description,
          read: read || requested.indexOf(`read:${id}`) > -1,
          write: write || requested.indexOf(`write:${id}`) > -1,
        }
      }).filter(c => {
        return c.read || c.write
      })
    }
  },
  methods: {
    fetchApplication () {
      this.isLoading = true
      let self = this
      axios.get(`oauth/apps/${this.clientId}/`).then((response) => {
        self.isLoading = false
        self.application = response.data
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    submit () {
      this.isLoading = true
      let self = this
      let data = new FormData();
      data.set('redirect_uri', this.redirectUri)
      data.set('scope', this.scope)
      data.set('allow', true)
      data.set('client_id', this.clientId)
      data.set('response_type', this.responseType)
      data.set('state', this.state)
      data.set('nonce', this.nonce)
      axios.post(`oauth/authorize/`, data, {headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'}}).then((response) => {
        if (self.redirectUri === 'urn:ietf:wg:oauth:2.0:oob') {
          self.isLoading = false
          self.code = response.data.code
        } else {
          window.location.href = response.data.redirect_uri
        }
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  }
}
</script>
