<template>
  <footer id="footer" role="contentinfo" class="ui vertical footer segment">
    <div class="ui container">
      <div class="ui stackable equal height stackable grid">
        <section class="four wide column">
          <h4 v-if="podName" class="ui header ellipsis">
            <span v-translate="{instanceName: podName}" translate-context="Footer/About/Title">About %{instanceName}</span>
          </h4>
          <h4 v-else class="ui header ellipsis">
            <span v-translate="{instanceUrl: instanceHostname}" translate-context="Footer/About/Title">About %{instanceUrl}</span>
          </h4>
          <div class="ui list">
            <router-link v-if="this.$route.path != '/about'" class="link item" to="/about">
              <translate translate-context="Footer/About/List item.Link">About page</translate>
            </router-link>
            <router-link v-else-if="this.$route.path == '/about' && $store.state.auth.authenticated" class="link item" to="/library">
              <translate translate-context="Footer/*/List item.Link">Go to Library</translate>
            </router-link>
            <router-link v-else class="link item" to="/">
              <translate translate-context="Footer/*/List item.Link">Home Page</translate>
            </router-link>
              <a v-if="version" class="link item" href="https://docs.funkwhale.audio/changelog.html" target="_blank">
                <translate translate-context="Footer/*/List item" :translate-params="{version: version}" >Version %{version}</translate>
              </a>
            <a role="button" href="" class="link item" @click.prevent="$emit('show:set-instance-modal')" >
              <translate translate-context="Footer/*/List item.Link">Use another instance</translate>
            </a>
          </div>
          <div class="ui form">
            <div class="ui field">
              <label for="language-select"><translate translate-context="Footer/Settings/Dropdown.Label/Short, Verb">Change language</translate></label>
              <select id="language-select" class="ui dropdown" :value="$language.current" @change="$store.dispatch('ui/currentLanguage', $event.target.value)">
                <option v-for="(language, key) in $language.available" :key="key" :value="key">{{ language }}</option>
              </select>
            </div>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate class="ui header" translate-context="Footer/*/Title">Using Funkwhale</h4>
          <div class="ui list">
            <a href="https://docs.funkwhale.audio" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link/Short, Noun">Documentation</translate></a>
            <a href="https://funkwhale.audio/apps" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Mobile and desktop apps</translate></a>
            <a hrelf="" class="link item" @click.prevent="$emit('show:shortcuts-modal')"><translate translate-context="*/*/*/Noun">Keyboard shortcuts</translate></a>
          </div>
          <div class="ui form">
            <div class="ui field">
              <label for="theme-select"><translate translate-context="Footer/Settings/Dropdown.Label/Short, Verb">Change theme</translate></label>
              <select id="theme-select" class="ui dropdown" :value="$store.state.ui.theme" @change="$store.dispatch('ui/theme', $event.target.value)">
                <option v-for="theme in themes" :key="theme.key" :value="theme.key">{{ theme.name }}</option>
              </select>
            </div>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate translate-context="Footer/*/Link" class="ui header">Getting help</h4>
          <div class="ui list">
            <a href="https://governance.funkwhale.audio/g/kQgxNq15/funkwhale" class="link item" target="_blank"><translate translate-context="Footer/*/Listitem.Link">Support forum</translate></a>
            <a href="https://riot.im/app/#/room/#funkwhale-troubleshooting:matrix.org" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Chat room</translate></a>
            <a href="https://dev.funkwhale.audio/funkwhale/funkwhale/issues" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Issue tracker</translate></a>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate class="ui header" translate-context="Footer/*/Title/Short">About Funkwhale</h4>
          <div class="ui list">
            <a href="https://funkwhale.audio" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Official website</translate></a>
            <a href="https://contribute.funkwhale.audio" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Contribute</translate></a>
            <a href="https://dev.funkwhale.audio/funkwhale/funkwhale" class="link item" target="_blank"><translate translate-context="Footer/*/List item.Link">Source code</translate></a>
          </div>
          <div class="ui hidden divider"></div>
          <p>
            <translate translate-context="Footer/*/List item.Link">The funkwhale logo was kindly designed and provided by Francis Gading.</translate>
          </p>
        </section>
      </div>
    </div>
  </footer>
</template>

<script>
import Vue from "vue"
import { mapState } from "vuex"
import axios from 'axios'
import _ from '@/lodash'

export default {
  props: ["version"],
  computed: {
    ...mapState({
      messages: state => state.ui.messages,
      nodeinfo: state => state.instance.nodeinfo,
    }),
    podName() {
      return _.get(this.nodeinfo, 'metadata.nodeName')
    },
    instanceHostname() {
      let url = this.$store.state.instance.instanceUrl
      let parser = document.createElement("a")
      parser.href = url
      return parser.hostname
    },
    themes () {
      return [
        {
          name: this.$pgettext('Footer/Settings/Dropdown.Label/Theme name', 'Light'),
          key: 'light'
        },
        {
          name: this.$pgettext('Footer/Settings/Dropdown.Label/Theme name', 'Dark'),
          key: 'dark'
        }
      ]
    }
  }
}
</script>
