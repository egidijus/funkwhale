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
          <div class="ui link list">
            <router-link class="item" to="/about">
              <translate translate-context="Footer/About/List item.Link">About page</translate>
            </router-link>
              <a v-if="version" class="item" href="https://docs.funkwhale.audio/changelog.html" target="_blank">
                <translate translate-context="Footer/*/List item" :translate-params="{version: version}" >Version %{version}</translate>
              </a>
            <div role="button" class="item" @click="$emit('show:set-instance-modal')" >
              <translate translate-context="Footer/*/List item.Link">Use another instance</translate>
            </div>
          </div>
          <div class="ui form">
            <div class="ui field">
              <label><translate translate-context="Footer/Settings/Dropdown.Label/Short, Verb">Change language</translate></label>
              <select class="ui dropdown" :value="$language.current" @change="$store.commit('ui/currentLanguage', $event.target.value)">
                <option v-for="(language, key) in $language.available" :key="key" :value="key">{{ language }}</option>
              </select>
            </div>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate class="ui header" translate-context="Footer/*/Title">Using Funkwhale</h4>
          <div class="ui link list">
            <a href="https://docs.funkwhale.audio" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link/Short, Noun">Documentation</translate></a>
            <a href="https://funkwhale.audio/apps" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Mobile and desktop apps</translate></a>
            <div role="button" class="item" @click="$emit('show:shortcuts-modal')"><translate translate-context="*/*/*/Noun">Keyboard shortcuts</translate></div>
          </div>
          <div class="ui form">
            <div class="ui field">
              <label><translate translate-context="Footer/Settings/Dropdown.Label/Short, Verb">Change theme</translate></label>
              <select class="ui dropdown" :value="$store.state.ui.theme" @change="$store.commit('ui/theme', $event.target.value)">
                <option v-for="theme in themes" :key="theme.key" :value="theme.key">{{ theme.name }}</option>
              </select>
            </div>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate translate-context="Footer/*/Link" class="ui header">Getting help</h4>
          <div class="ui link list">
            <a href="https://governance.funkwhale.audio/g/kQgxNq15/funkwhale" class="item" target="_blank"><translate translate-context="Footer/*/Listitem.Link">Support forum</translate></a>
            <a href="https://riot.im/app/#/room/#funkwhale-troubleshooting:matrix.org" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Chat room</translate></a>
            <a href="https://dev.funkwhale.audio/funkwhale/funkwhale/issues" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Issue tracker</translate></a>
          </div>
        </section>
        <section class="four wide column">
          <h4 v-translate class="ui header" translate-context="Footer/*/Title/Short">About Funkwhale</h4>
          <div class="ui link list">
            <a href="https://funkwhale.audio" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Official website</translate></a>
            <a href="https://contribute.funkwhale.audio" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Contribute</translate></a>
            <a href="https://dev.funkwhale.audio/funkwhale/funkwhale" class="item" target="_blank"><translate translate-context="Footer/*/List item.Link">Source code</translate></a>
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
