<template>
  <div id="app" :key="String($store.state.instance.instanceUrl)" :class="[$store.state.ui.queueFocused ? 'queue-focused' : '', {'has-bottom-player': $store.state.queue.tracks.length > 0}, `is-${ $store.getters['ui/windowSize']}`]">
    <!-- here, we display custom stylesheets, if any -->
    <link
      v-for="url in customStylesheets"
      rel="stylesheet"
      property="stylesheet"
      :href="url"
      :key="url"
    >
    <template>
      <sidebar></sidebar>
      <set-instance-modal @update:show="showSetInstanceModal = $event" :show="showSetInstanceModal"></set-instance-modal>
      <service-messages></service-messages>
      <transition name="queue">
        <queue @touch-progress="$refs.player.setCurrentTime($event)" v-if="$store.state.ui.queueFocused"></queue>
      </transition>
      <router-view :class="{hidden: $store.state.ui.queueFocused}"></router-view>
      <player ref="player"></player>
      <app-footer
        :class="{hidden: $store.state.ui.queueFocused}"
        :version="version"
        @show:shortcuts-modal="showShortcutsModal = !showShortcutsModal"
        @show:set-instance-modal="showSetInstanceModal = !showSetInstanceModal"
      ></app-footer>
      <playlist-modal v-if="$store.state.auth.authenticated"></playlist-modal>
      <channel-upload-modal v-if="$store.state.auth.authenticated"></channel-upload-modal>
      <filter-modal v-if="$store.state.auth.authenticated"></filter-modal>
      <report-modal></report-modal>
      <shortcuts-modal @update:show="showShortcutsModal = $event" :show="showShortcutsModal"></shortcuts-modal>
      <GlobalEvents @keydown.h.exact="showShortcutsModal = !showShortcutsModal"/>
    </template>
  </div>
</template>

<script>
import Vue from 'vue'
import axios from 'axios'
import _ from '@/lodash'
import {mapState, mapGetters, mapActions} from 'vuex'
import { WebSocketBridge } from 'django-channels'
import GlobalEvents from '@/components/utils/global-events'
import moment from  'moment'
import locales from './locales'
import {getClientOnlyRadio} from '@/radios'

export default {
  name: 'app',
  components: {
    Player:  () => import(/* webpackChunkName: "audio" */ "@/components/audio/Player"),
    Queue:  () => import(/* webpackChunkName: "audio" */ "@/components/Queue"),
    PlaylistModal:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/playlists/PlaylistModal"),
    ChannelUploadModal:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/channels/UploadModal"),
    Sidebar:  () => import(/* webpackChunkName: "core" */ "@/components/Sidebar"),
    AppFooter:  () => import(/* webpackChunkName: "core" */ "@/components/Footer"),
    ServiceMessages:  () => import(/* webpackChunkName: "core" */ "@/components/ServiceMessages"),
    SetInstanceModal:  () => import(/* webpackChunkName: "core" */ "@/components/SetInstanceModal"),
    ShortcutsModal:  () => import(/* webpackChunkName: "core" */ "@/components/ShortcutsModal"),
    FilterModal:  () => import(/* webpackChunkName: "moderation" */ "@/components/moderation/FilterModal"),
    ReportModal:  () => import(/* webpackChunkName: "moderation" */ "@/components/moderation/ReportModal"),
    GlobalEvents,
  },
  data () {
    return {
      bridge: null,
      instanceUrl: null,
      showShortcutsModal: false,
      showSetInstanceModal: false,
      initialTitle: document.title,
    }
  },
  async created () {

    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener(
        'controllerchange', () => {
          if (this.serviceWorker.refreshing) return;
          this.$store.commit('ui/serviceWorker', {
            refreshing: true
          })
          window.location.reload();
        }
      );
    }

    this.openWebsocket()
    let self = this
    if (!this.$store.state.ui.selectedLanguage) {
      this.autodetectLanguage()
    }
    setInterval(() => {
      // used to redraw ago dates every minute
      self.$store.commit('ui/computeLastDate')
    }, 1000 * 60)
    const urlParams = new URLSearchParams(window.location.search);
    const serverUrl = urlParams.get('_server')
    if (serverUrl) {
      this.$store.commit('instance/instanceUrl', serverUrl)
    }
    const url = urlParams.get('_url')
    if (url) {
      this.$router.replace(url)
    }
    else if (!this.$store.state.instance.instanceUrl) {
      // we have several way to guess the API server url. By order of precedence:
      // 1. use the url provided in settings.json, if any
      // 2. use the url specified when building via VUE_APP_INSTANCE_URL
      // 3. use the current url
      let defaultInstanceUrl = this.$store.state.instance.frontSettings.defaultServerUrl || process.env.VUE_APP_INSTANCE_URL || this.$store.getters['instance/defaultUrl']()
      this.$store.commit('instance/instanceUrl', defaultInstanceUrl)
    } else {
      // needed to trigger initialization of axios / service worker
      this.$store.commit('instance/instanceUrl', this.$store.state.instance.instanceUrl)
    }
    await this.fetchNodeInfo()
    this.$store.dispatch('auth/check')
    setInterval(() => {
      // used to refresh profile every now and then (important for refreshing scoped tokens)
      self.$store.dispatch('auth/check')
    }, 1000 * 60 * 60 * 8)
    this.$store.dispatch('instance/fetchSettings')
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'inbox.item_added',
      id: 'sidebarCount',
      handler: this.incrementNotificationCountInSidebar
    })
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'mutation.created',
      id: 'sidebarReviewEditCount',
      handler: this.incrementReviewEditCountInSidebar
    })
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'mutation.updated',
      id: 'sidebarReviewEditCount',
      handler: this.incrementReviewEditCountInSidebar
    })
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'report.created',
      id: 'sidebarPendingReviewReportCount',
      handler: this.incrementPendingReviewReportsCountInSidebar
    })
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'user_request.created',
      id: 'sidebarPendingReviewRequestCount',
      handler: this.incrementPendingReviewRequestsCountInSidebar
    })
    this.$store.commit('ui/addWebsocketEventHandler', {
      eventName: 'Listen',
      id: 'handleListen',
      handler: this.handleListen
    })
  },
  mounted () {
    let self = this
    // slight hack to allow use to have internal links in <translate> tags
    // while preserving router behaviour
    document.documentElement.addEventListener('click', function (event) {
      if (!event.target.matches('a.internal')) return;
      self.$router.push(event.target.getAttribute('href'))
      event.preventDefault();
    }, false);
    this.$nextTick(() => {
      document.getElementById('fake-content').classList.add('loaded')
    })

  },
  destroyed () {
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'inbox.item_added',
      id: 'sidebarCount',
    })
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'mutation.created',
      id: 'sidebarReviewEditCount',
    })
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'mutation.updated',
      id: 'sidebarReviewEditCount',
    })
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'mutation.updated',
      id: 'sidebarPendingReviewReportCount',
    })
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'user_request.created',
      id: 'sidebarPendingReviewRequestCount',
    })
    this.$store.commit('ui/removeWebsocketEventHandler', {
      eventName: 'Listen',
      id: 'handleListen',
    })
    this.disconnect()
  },
  methods: {
    incrementNotificationCountInSidebar (event) {
      this.$store.commit('ui/incrementNotifications', {type: 'inbox', count: 1})
    },
    incrementReviewEditCountInSidebar (event) {
      this.$store.commit('ui/incrementNotifications', {type: 'pendingReviewEdits', value: event.pending_review_count})
    },
    incrementPendingReviewReportsCountInSidebar (event) {
      this.$store.commit('ui/incrementNotifications', {type: 'pendingReviewReports', value: event.unresolved_count})
    },
    incrementPendingReviewRequestsCountInSidebar (event) {
      this.$store.commit('ui/incrementNotifications', {type: 'pendingReviewRequests', value: event.pending_count})
    },
    handleListen (event) {
      if (this.$store.state.radios.current && this.$store.state.radios.running) {
        let current = this.$store.state.radios.current
        if (current.clientOnly && current.type === 'account') {
          getClientOnlyRadio(current).handleListen(current, event, this.$store)
        }
      }
    },
    async fetchNodeInfo () {
      let response = await axios.get('instance/nodeinfo/2.0/')
      this.$store.commit('instance/nodeinfo', response.data)
    },
    autodetectLanguage () {
      let userLanguage = navigator.language || navigator.userLanguage
      let available = locales.locales.map(e => { return e.code })
      let self = this
      let candidate
      let matching = available.filter((a) => {
        return userLanguage.replace('-', '_') === a
      })
      let almostMatching = available.filter((a) => {
        return userLanguage.replace('-', '_').split('_')[0] === a.split('_')[0]
      })
      if (matching.length > 0) {
        candidate = matching[0]
      } else if (almostMatching.length > 0) {
        candidate = almostMatching[0]
      } else {
        return
      }
      this.$store.commit('ui/currentLanguage', candidate)
    },
    disconnect () {
      if (!this.bridge) {
        return
      }
      this.bridge.socket.close(1000, 'goodbye', {keepClosed: true})
    },
    openWebsocket () {
      if (!this.$store.state.auth.authenticated) {
        return
      }
      this.disconnect()
      let self = this
      let token = this.$store.state.auth.token
      // let token = 'test'
      const bridge = new WebSocketBridge()
      this.bridge = bridge
      let url = this.$store.getters['instance/absoluteUrl'](`api/v1/activity?token=${token}`)
      url = url.replace('http://', 'ws://')
      url = url.replace('https://', 'wss://')
      bridge.connect(
        url,
        [],
        {reconnectInterval: 1000 * 60})
      bridge.listen(function (event) {
        self.$store.dispatch('ui/websocketEvent', event)
      })
      bridge.socket.addEventListener('open', function () {
        console.log('Connected to WebSocket')
      })
    },
    getTrackInformationText(track) {
      const trackTitle = track.title
      const albumArtist = (track.album) ? track.album.artist.name : null
      const artistName = (
        (track.artist) ? track.artist.name : albumArtist)
      const text = `♫ ${trackTitle} – ${artistName} ♫`
      return text
    },
    updateDocumentTitle() {
      let parts = []
      const currentTrackPart = (
        (this.currentTrack) ? this.getTrackInformationText(this.currentTrack)
        : null)
      if (currentTrackPart) {
        parts.push(currentTrackPart)
      }
      if (this.$store.state.ui.pageTitle) {
        parts.push(this.$store.state.ui.pageTitle)
      }
      parts.push(this.initialTitle || 'Funkwhale')
      document.title = parts.join(' – ')
    },

    updateApp () {
      this.$store.commit('ui/serviceWorker', {updateAvailable: false})
      if (!this.serviceWorker.registration || !this.serviceWorker.registration.waiting) { return; }
      this.serviceWorker.registration.waiting.postMessage({command: 'skipWaiting'})
    }
  },
  computed: {
    ...mapState({
      messages: state => state.ui.messages,
      nodeinfo: state => state.instance.nodeinfo,
      playing: state => state.player.playing,
      bufferProgress: state => state.player.bufferProgress,
      isLoadingAudio: state => state.player.isLoadingAudio,
      serviceWorker: state => state.ui.serviceWorker,
    }),
    ...mapGetters({
      hasNext: "queue/hasNext",
      currentTrack: 'queue/currentTrack',
      progress: "player/progress",
    }),
    labels() {
      let play = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Play track")
      let pause = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Pause track")
      let next = this.$pgettext('Sidebar/Player/Icon.Tooltip', "Next track")
      let expandQueue = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Expand queue")
      return {
        play,
        pause,
        next,
        expandQueue,
      }
    },
    suggestedInstances () {
      let instances = this.$store.state.instance.knownInstances.slice(0)
      if (this.$store.state.instance.frontSettings.defaultServerUrl) {
        let serverUrl = this.$store.state.instance.frontSettings.defaultServerUrl
        if (!serverUrl.endsWith('/')) {
          serverUrl = serverUrl + '/'
        }
        instances.push(serverUrl)
      }
      instances.push(this.$store.getters['instance/defaultUrl'](), 'https://demo.funkwhale.audio/')
      return _.uniq(instances.filter((e) => {return e}))
    },
    version () {
      if (!this.nodeinfo) {
        return null
      }
      return _.get(this.nodeinfo, 'software.version')
    },
    customStylesheets () {
      if (this.$store.state.instance.frontSettings) {
        return this.$store.state.instance.frontSettings.additionalStylesheets || []
      }
    },
  },
  watch: {
    '$store.state.instance.instanceUrl' (v) {
      this.$store.dispatch('instance/fetchSettings')
      this.fetchNodeInfo()
    },
    '$store.state.ui.theme': {
      immediate: true,
      handler (newValue, oldValue) {
        let oldTheme = oldValue || 'light'
        document.body.classList.remove(`theme-${oldTheme}`)
        document.body.classList.add(`theme-${newValue}`)
      },
    },
    '$store.state.auth.authenticated' (newValue) {
      if (!newValue) {
        this.disconnect()
      } else {
        this.openWebsocket()
      }
    },
    '$store.state.ui.currentLanguage': {
      immediate: true,
      handler(newValue) {
        let self = this
        if (newValue === 'en_US') {
          self.$language.current = 'noop'
          self.$language.current = newValue
          return self.$store.commit('ui/momentLocale', 'en')
        }
        import(/* webpackChunkName: "locale-[request]" */ `./translations/${newValue}.json`).then((response) =>{
          Vue.$translations[newValue] = response.default[newValue]
        }).finally(() => {
          // set current language twice, otherwise we seem to have a cache somewhere
          // and rendering does not happen
          self.$language.current = 'noop'
          self.$language.current = newValue
        })
        let momentLocale = newValue.replace('_', '-').toLowerCase()
        import(/* webpackChunkName: "moment-locale-[request]" */ `moment/locale/${momentLocale}.js`).then(() => {
          self.$store.commit('ui/momentLocale', momentLocale)
        }).catch(() => {
          console.log('No momentjs locale available for', momentLocale)
          let shortLocale = momentLocale.split('-')[0]
          import(/* webpackChunkName: "moment-locale-[request]" */ `moment/locale/${shortLocale}.js`).then(() => {
            self.$store.commit('ui/momentLocale', shortLocale)
          }).catch(() => {
            console.log('No momentjs locale available for', shortLocale)
          })
        })
      }
    },
    'currentTrack': {
      immediate: true,
      handler(newValue) {
        this.updateDocumentTitle()
      },
    },
    '$store.state.ui.pageTitle': {
      immediate: true,
      handler(newValue) {
        this.updateDocumentTitle()
      },
    },
    'serviceWorker.updateAvailable': {
      handler (v) {
        if (!v) {
          return
        }
        let self = this
        this.$store.commit('ui/addMessage', {
          content: this.$pgettext("App/Message/Paragraph", "A new version of the app is available."),
          date: new Date(),
          key: 'refreshApp',
          displayTime: 0,
          classActions: 'bottom attached opaque',
          actions: [
            {
              text: this.$pgettext("App/Message/Paragraph", "Update"),
              class: "primary",
              click: function () {
                self.updateApp()
              },
            },
            {
              text: this.$pgettext("App/Message/Paragraph", "Later"),
              class: "basic",
            }
          ]
        })
      },
      immediate: true,
    }
  }
}
</script>

<style lang="scss">
@import "style/_main";

.ui.bottom-player {
  z-index: 999999;
  width: 100%;
  width: 100vw;
  .ui.top.attached.progress {
    top: 0;
  }
}
.dimmed {
  .ui.bottom-player {
    @include media("<desktop") {
      z-index: 0;
    }
  }
}
#app.queue-focused {
  .queue-not-focused {
    @include media("<desktop") {
      display: none;
    }
  }
}
.when-queue-focused {
  .group {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 1.1em;
    > * {
      margin-left: 0.5em;
    }
  }
  @include media("<desktop") {
    width: 100%;
    justify-content: space-between !important;
  }
}
#app:not(.queue-focused) {
  .when-queue-focused {
    @include media("<desktop") {
      display: none;
    }
  }
}
.ui.bottom-player > .segment.fixed-controls {
  width: 100%;
  width: 100vw;
  border-radius: 0;
  padding: 0em;
  position: fixed;
  bottom: 0;
  left: 0;
  margin: 0;
  z-index: 1001;
  height: $bottom-player-height;
  .controls-row {
    height: $bottom-player-height;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    @include media(">desktop") {
      padding: 0 1em;
      justify-content: space-around;
    }
  }
  cursor: pointer;
  .indicating.progress {
    overflow: hidden;
  }

  .ui.progress .bar {
    transition: none;
  }

  .ui.progress .buffer.bar {
    position: absolute;
  }

  @keyframes MOVE-BG {
    from {
      transform: translateX(0px);
    }
    to {
      transform: translateX(46px);
    }
  }
  .discrete.link {
    color: inherit;
  }
  .indicating.progress .bar {
    left: -46px;
    width: 200% !important;
    color: grey;
    background: repeating-linear-gradient(
      -55deg,
      grey 1px,
      grey 10px,
      transparent 10px,
      transparent 20px
    ) !important;

    animation-name: MOVE-BG;
    animation-duration: 2s;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
  }
  .ui.progress:not([data-percent]):not(.indeterminate)
    .bar.position:not(.buffer) {
    background: #ff851b;
    min-width: 0;
  }

  .track-controls {
    display: flex;
    align-items: center;
    justify-content: start;
    flex-grow: 1;
    .image {
      padding: 0.5em;
      width: auto;
      margin-right: 0.5em;
      > img {
        max-height: 3.7em;
        max-width: 4.7em;
      }
    }
  }
  .controls {
    min-width: 8em;
    font-size: 1.1em;
    @include media(">desktop") {
      &:not(.fluid) {
        width: 20%;
      }
      &.queue-controls {
        width: 32.5%;
      }
      &.progress-controls {
        width: 10%;
      }
      &.player-controls {
        width: 15%;
      }
    }
    &.small, .small {
      @include media(">desktop") {
        font-size: 0.9em;
      }
    }
    .icon {
      font-size: 1.1em;
    }
    .icon.large {
      font-size: 1.4em;
    }
    &:not(.track-controls) {
      @include media(">desktop") {
        line-height: 1em;
      }
      justify-content: center;
      align-items: center;
      &.align-right {
        justify-content: flex-end;
      }
      &.align-left {
        justify-content: flex-start;
      }
      > * {
        padding: 0.5em;
      }
    }
    &.player-controls {
      .icon {
        margin: 0;
      }
    }

  }
}
.queue-enter-active, .queue-leave-active {
  transition: all 0.2s ease-in-out;
  .current-track, .queue-column {
    opacity: 0;
  }
}
.queue-enter, .queue-leave-to {
  transform: translateY(100vh);
  opacity: 0;
}
</style>
