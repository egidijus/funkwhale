<template>
  <modal @update:show="$emit('update:show', $event); isError = false" :show="show">
    <div class="header"><translate translate-context="Popup/Instance/Title">Choose your instance</translate></div>
    <div class="scrolling content">
      <div v-if="isError" role="alert" class="ui negative message">
        <div class="header"><translate translate-context="Popup/Instance/Error message.Title">It is not possible to connect to the given URL</translate></div>
        <ul class="list">
          <li><translate translate-context="Popup/Instance/Error message.List item">The server might be down</translate></li>
          <li><translate translate-context="Popup/Instance/Error message.List item">The given address is not a Funkwhale server</translate></li>
        </ul>
      </div>
      <form class="ui form" @submit.prevent="checkAndSwitch(instanceUrl)">
        <p v-if="$store.state.instance.instanceUrl" class="description" translate-context="Popup/Login/Paragraph" v-translate="{url: $store.state.instance.instanceUrl, hostname: instanceHostname }">
            You are currently connected to <a href="%{ url }" target="_blank">%{ hostname }&nbsp;<i class="external icon"></i></a>. If you continue, you will be disconnected from your current instance and all your local data will be deleted.
        </p>
        <p v-else>
          <translate translate-context="Popup/Instance/Paragraph">To continue, please select the Funkwhale instance you want to connect to. Enter the address directly, or select one of the suggested choices.</translate>
        </p>
        <div class="field">
          <label><translate translate-context="Popup/Instance/Input.Label/Noun">Instance URL</translate></label>
          <div class="ui action input">
            <input type="text" v-model="instanceUrl" placeholder="https://funkwhale.server">
            <button type="submit" :class="['ui', 'icon', {loading: isLoading}, 'button']">
              <translate translate-context="*/*/Button.Label/Verb">Submit</translate>
            </button>
          </div>
        </div>
      </form>
      <div class="ui hidden divider"></div>
      <form class="ui form" @submit.prevent="">
        <div class="field">
          <label><translate translate-context="Popup/Instance/List.Label">Suggested choices</translate></label>
          <button v-for="url in suggestedInstances" @click="checkAndSwitch(url)" class="ui basic button">{{ url }}</button>
        </div>
      </form>
    </div>
    <div class="actions">
      <div class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></div>
    </div>
  </modal>
</template>

<script>
import Modal from '@/components/semantic/Modal'
import axios from 'axios'
import _ from "@/lodash"

export default {
  props: ['show'],
  components: {
    Modal,
  },
  data() {
    return {
      instanceUrl: null,
      nodeinfo: null,
      isError: false,
      isLoading: false,
      path: 'api/v1/instance/nodeinfo/2.0/',
    }
  },
  methods: {
    fetchNodeInfo () {
      let self = this
      axios.get('instance/nodeinfo/2.0/').then(response => {
        self.nodeinfo = response.data
      })
    },
    fetchUrl (url) {
      let urlFetch = url
      if (!urlFetch.endsWith('/')) {
        urlFetch = `${urlFetch}/${this.path}`
      } else {
        urlFetch =  `${urlFetch}${this.path}`
      }
      if (!urlFetch.startsWith('https://') && !urlFetch.startsWith('http://')) {
        urlFetch = `https://${urlFetch}`
      }
      return urlFetch
    },
    requestDistantNodeInfo (url) {
      var self = this
      axios.get(this.fetchUrl(url)).then(function (response) {
        self.isLoading = false
        if(!url.startsWith('https://') && !url.startsWith('http://')) {
          url = `https://${url}`
        }
        self.switchInstance(url)
      }).catch(function (error) {
        self.isLoading = false
        self.isError = true
      })
    },
    switchInstance (url) {
      // Here we disconnect from the current instance and reconnect to the new one. No check is performed…
      this.$emit('update:show', false)
      this.isError = false
      let msg = this.$pgettext('*/Instance/Message', 'You are now using the Funkwhale instance at %{ url }')
      this.$store.commit('ui/addMessage', {
        content: this.$gettextInterpolate(msg, {url: url}),
        date: new Date()
      })
      let self = this
      this.$nextTick(() => {
        self.$store.commit('instance/instanceUrl', null)
        self.$store.dispatch('instance/setUrl', url)
      })
    },
    checkAndSwitch (url) {
      // First we have to check if the address is a valid FW server. If yes, we switch:
      this.isError = false // Clear error message if any…
      this.isLoading = true
      this.requestDistantNodeInfo(url)
    },
  },
  computed: {
    suggestedInstances () {
      let instances = this.$store.state.instance.knownInstances.slice(0)
      if (this.$store.state.instance.frontSettings.defaultServerUrl) {
        let serverUrl = this.$store.state.instance.frontSettings.defaultServerUrl
        if (!serverUrl.endsWith('/')) {
          serverUrl = serverUrl + '/'
        }
        instances.push(serverUrl)
      }
      let self = this
      instances.push(this.$store.getters['instance/defaultUrl'](), 'https://demo.funkwhale.audio/')
      return _.uniq(instances.filter((e) => {return e != self.$store.state.instance.instanceUrl}))
    },
    instanceHostname() {
      let url = this.$store.state.instance.instanceUrl
      let parser = document.createElement("a")
      parser.href = url
      return parser.hostname
    },
  },
  watch: {
    '$store.state.instance.instanceUrl' () {
      this.$store.dispatch('instance/fetchSettings')
      this.fetchNodeInfo()
    },
  },
}
</script>

<style scoped>
</style>
