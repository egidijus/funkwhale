<template>
  <section role="complementary" v-if="currentTrack" class="player-wrapper ui bottom-player component-player" aria-labelledby="player-label">
    <h1 id="player-label" class="visually-hidden">
      <translate translate-context="*/*/*">Audio player and controls</translate>
    </h1>
    <div class="ui inverted segment fixed-controls" @click.prevent.stop="toggleMobilePlayer">
      <div
        :class="['ui', 'top attached', 'small', 'inverted', {'indicating': isLoadingAudio}, 'progress']">
        <div class="buffer bar" :data-percent="bufferProgress" :style="{ 'width': bufferProgress + '%' }"></div>
        <div class="position bar" :data-percent="progress" :style="{ 'width': progress + '%' }"></div>
      </div>
      <div class="controls-row">

        <div class="controls track-controls queue-not-focused desktop-and-up">
          <div class="ui tiny image" @click.stop.prevent="$router.push({name: 'library.tracks.detail', params: {id: currentTrack.id }})">
            <img alt="" ref="cover" v-if="currentTrack.cover && currentTrack.cover.urls.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.cover.urls.medium_square_crop)">
            <img alt="" ref="cover" v-else-if="currentTrack.album && currentTrack.album.cover && currentTrack.album.cover.urls && currentTrack.album.cover.urls.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.album.cover.urls.medium_square_crop)">
            <img alt="" v-else src="../../assets/audio/default-cover.png">
          </div>
          <div @click.stop.prevent="" class="middle aligned content ellipsis">
            <strong>
              <router-link @click.stop.prevent="" class="small header discrete link track" :to="{name: 'library.tracks.detail', params: {id: currentTrack.id }}">
                {{ currentTrack.title }}
              </router-link>
            </strong>
            <div class="meta">
              <router-link @click.stop.prevent="" class="discrete link" :to="{name: 'library.artists.detail', params: {id: currentTrack.artist.id }}">
                {{ currentTrack.artist.name }}</router-link><template v-if="currentTrack.album"> /<router-link @click.stop.prevent="" class="discrete link" :to="{name: 'library.albums.detail', params: {id: currentTrack.album.id }}">
                {{ currentTrack.album.title }}
              </router-link></template>
            </div>
          </div>
        </div>
        <div class="controls track-controls queue-not-focused tablet-and-below">
          <div class="ui tiny image">
            <img alt="" ref="cover" v-if="currentTrack.cover && currentTrack.cover.urls.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.cover.urls.medium_square_crop)">
            <img alt="" ref="cover" v-else-if="currentTrack.album && currentTrack.album.cover && currentTrack.album.cover.urls.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.album.cover.urls.medium_square_crop)">
            <img alt="" v-else src="../../assets/audio/default-cover.png">
          </div>
          <div class="middle aligned content ellipsis">
            <strong>
              {{ currentTrack.title }}
            </strong>
            <div class="meta">
              {{ currentTrack.artist.name }}<template v-if="currentTrack.album"> / {{ currentTrack.album.title }}</template>
            </div>
          </div>
        </div>
        <div class="controls desktop-and-up fluid align-right" v-if="$store.state.auth.authenticated">
          <track-favorite-icon
            class="control white"
            :track="currentTrack"></track-favorite-icon>
          <track-playlist-icon
            class="control white"
            :track="currentTrack"></track-playlist-icon>
          <button
            @click="$store.dispatch('moderation/hide', {type: 'artist', target: currentTrack.artist})"
            :class="['ui', 'really', 'basic', 'circular', 'icon', 'button', 'control']"
            :aria-label="labels.addArtistContentFilter"
            :title="labels.addArtistContentFilter">
            <i :class="['eye slash outline', 'basic', 'icon']"></i>
          </button>
        </div>
        <div class="player-controls controls queue-not-focused">
          <button
            :title="labels.previous"
            :aria-label="labels.previous"
            class="circular button control tablet-and-up"
            @click.prevent.stop="$store.dispatch('queue/previous')"
            :disabled="!hasPrevious">
              <i :class="['ui', 'large', {'disabled': !hasPrevious}, 'backward step', 'icon']" ></i>
          </button>
          <button
            v-if="!playing"
            :title="labels.play"
            :aria-label="labels.play"
            @click.prevent.stop="togglePlay"
            class="circular button control">
              <i :class="['ui', 'big', 'play', {'disabled': !currentTrack}, 'icon']"></i>
          </button>
          <button
            v-else
            :title="labels.pause"
            :aria-label="labels.pause"
            @click.prevent.stop="togglePlay"
            class="circular button control">
              <i :class="['ui', 'big', 'pause', {'disabled': !currentTrack}, 'icon']"></i>
          </button>
          <button
            :title="labels.next"
            :aria-label="labels.next"
            class="circular button control"
            @click.prevent.stop="$store.dispatch('queue/next')"
            :disabled="!hasNext">
              <i :class="['ui', 'large', {'disabled': !hasNext}, 'forward step', 'icon']" ></i>
          </button>
        </div>

        <div class="controls progress-controls queue-not-focused tablet-and-up small align-left">
          <div class="timer">
            <template v-if="!isLoadingAudio">
              <span class="start" @click.stop.prevent="setCurrentTime(0)">{{currentTimeFormatted}}</span>
              | <span class="total">{{durationFormatted}}</span>
            </template>
            <template v-else>
              00:00 | 00:00
            </template>
          </div>
        </div>
        <div class="controls queue-controls when-queue-focused align-right">
          <div class="group">
            <volume-control class="expandable" />
            <button
              class="circular control button"
              v-if="looping === 0"
              :title="labels.loopingDisabled"
              :aria-label="labels.loopingDisabled"
              @click.prevent.stop="$store.commit('player/looping', 1)"
              :disabled="!currentTrack">
              <i :class="['ui', {'disabled': !currentTrack}, 'step', 'repeat', 'icon']"></i>
            </button>
            <button
              class="looping circular control button"
              @click.prevent.stop="$store.commit('player/looping', 2)"
              :title="labels.loopingSingle"
              :aria-label="labels.loopingSingle"
              v-if="looping === 1"
              :disabled="!currentTrack">
              <i
                class="repeat icon">
                <span class="ui circular tiny vibrant label">1</span>
              </i>
            </button>
            <button
              class="looping circular control button"
              :title="labels.loopingWhole"
              :aria-label="labels.loopingWhole"
              v-if="looping === 2"
              :disabled="!currentTrack"
              @click.prevent.stop="$store.commit('player/looping', 0)">
              <i
                class="repeat icon">
                <span class="ui circular tiny vibrant label">&infin;</span>
              </i>
            </button>
            <button
              class="circular control button"
              :disabled="queue.tracks.length === 0"
              :title="labels.shuffle"
              :aria-label="labels.shuffle"
              @click.prevent.stop="shuffle()">
              <div v-if="isShuffling" class="ui inline shuffling inverted tiny active loader"></div>
              <i v-else :class="['ui', 'random', {'disabled': queue.tracks.length === 0}, 'icon']" ></i>
            </button>
          </div>
          <div class="group">
            <div class="fake-dropdown">
              <button class="position circular control button desktop-and-up" @click.stop="toggleMobilePlayer" aria-expanded="true">
                <i class="stream icon"></i>
                <translate translate-context="Sidebar/Queue/Text" :translate-params="{index: queue.currentIndex + 1, length: queue.tracks.length}">
                  %{ index } of %{ length }
                </translate>
              </button>
              <button class="position circular control button tablet-and-below" @click.stop="switchTab">
                <i class="stream icon"></i>
                <translate translate-context="Sidebar/Queue/Text" :translate-params="{index: queue.currentIndex + 1, length: queue.tracks.length}">
                  %{ index } of %{ length }
                </translate>
              </button>

              <button
                class="circular control button close-control desktop-and-up"
                v-if="$store.state.ui.queueFocused"
                @click.stop="toggleMobilePlayer">
                <i class="large down angle icon"></i>
              </button>
              <button
                class="circular control button desktop-and-up"
                v-else
                @click.stop="toggleMobilePlayer">
                <i class="large up angle icon"></i>
              </button>
              <button
                class="circular control button close-control tablet-and-below"
                v-if="$store.state.ui.queueFocused === 'player'"
                @click.stop="switchTab">
                <i class="large up angle icon"></i>
              </button>
              <button
                class="circular control button tablet-and-below"
                v-if="$store.state.ui.queueFocused === 'queue'"
                @click.stop="switchTab">
                <i class="large down angle icon"></i>
              </button>
            </div>
            <button
              class="circular control button close-control tablet-and-below"
              @click.stop="$store.commit('ui/queueFocused', null)">
              <i class="x icon"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
    <GlobalEvents
      @keydown.p.prevent.exact="togglePlay"
      @keydown.esc.prevent.exact="$store.commit('ui/queueFocused', null)"
      @keydown.ctrl.shift.left.prevent.exact="previous"
      @keydown.ctrl.shift.right.prevent.exact="next"
      @keydown.shift.down.prevent.exact="$store.commit('player/incrementVolume', -0.1)"
      @keydown.shift.up.prevent.exact="$store.commit('player/incrementVolume', 0.1)"
      @keydown.right.prevent.exact="seek (5)"
      @keydown.left.prevent.exact="seek (-5)"
      @keydown.shift.right.prevent.exact="seek (30)"
      @keydown.shift.left.prevent.exact="seek (-30)"
      @keydown.m.prevent.exact="toggleMute"
      @keydown.l.exact="$store.commit('player/toggleLooping')"
      @keydown.s.exact="shuffle"
      @keydown.f.exact="$store.dispatch('favorites/toggle', currentTrack.id)"
      @keydown.q.exact="clean"
      @keydown.e.exact="toggleMobilePlayer"
      />
  </section>
</template>

<script>
import { mapState, mapGetters, mapActions } from "vuex"
import GlobalEvents from "@/components/utils/global-events"
import { Howl } from "howler"
import $ from 'jquery'
import _ from '@/lodash'
import url from '@/utils/url'
import axios from 'axios'

export default {
  components: {
    VolumeControl:  () => import(/* webpackChunkName: "audio" */ "./VolumeControl"),
    TrackFavoriteIcon:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/favorites/TrackFavoriteIcon"),
    TrackPlaylistIcon:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/playlists/TrackPlaylistIcon"),
    GlobalEvents,
  },
  data() {
    return {
      isShuffling: false,
      sliderVolume: this.volume,
      showVolume: false,
      currentSound: null,
      dummyAudio: null,
      isUpdatingTime: false,
      sourceErrors: 0,
      progressInterval: null,
      maxPreloaded: 3,
      preloadDelay: 15,
      listenDelay: 15,
      listeningRecorded: null,
      soundsCache: [],
      soundId: null,
      playTimeout: null,
      nextTrackPreloaded: false
    }
  },
  mounted() {
    this.$store.dispatch('player/updateProgress', 0)
    this.$store.commit('player/playing', false)
    this.$store.commit("player/isLoadingAudio", false)
    Howler.unload()  // clear existing cache, if any
    this.nextTrackPreloaded = false
    // we trigger the watcher explicitely it does not work otherwise
    this.sliderVolume = this.volume
    // this is needed to unlock audio playing under some browsers,
    // cf https://github.com/goldfire/howler.js#mobilechrome-playback
    // but we never actually load those audio files
    this.dummyAudio = new Howl({
      preload: false,
      autoplay: false,
      src: ["noop.webm", "noop.mp3"]
    })
    if (this.currentTrack) {
      this.getSound(this.currentTrack)
      this.updateMetadata()
    }
    // Add controls for notification drawer
    if ('mediaSession' in navigator) {
      navigator.mediaSession.setActionHandler('play', this.togglePlay);
      navigator.mediaSession.setActionHandler('pause', this.togglePlay);
      navigator.mediaSession.setActionHandler('seekforward', this.seekForward);
      navigator.mediaSession.setActionHandler('seekbackward', this.seekBackward);
      navigator.mediaSession.setActionHandler('nexttrack', this.next);
      navigator.mediaSession.setActionHandler('previoustrack', this.previous);
    }
  },
  beforeDestroy () {
    this.dummyAudio.unload()
    this.observeProgress(false)
  },
  destroyed() {
  },
  methods: {
    ...mapActions({
      togglePlay: "player/togglePlay",
      mute: "player/mute",
      unmute: "player/unmute",
      clean: "queue/clean",
      toggleMute: "player/toggleMute",
    }),
    async getTrackData (trackData) {
      let data = null
      if (!trackData.uploads.length || trackData.uploads.length === 0) {
        // we don't have upload informations for this track, we need to fetch it
        await axios.get(`tracks/${trackData.id}/`).then((response) => {
          data = response.data
        }, error => {
          data = null
        })
      } else {
        return trackData
      }
      if (data === null) {
        return
      }
      return data
    },
    shuffle() {
      let disabled = this.queue.tracks.length === 0
      if (this.isShuffling || disabled) {
        return
      }
      let self = this
      let msg = this.$pgettext('Content/Queue/Message', "Queue shuffled!")
      this.isShuffling = true
      setTimeout(() => {
        self.$store.dispatch("queue/shuffle", () => {
          self.isShuffling = false
          self.$store.commit("ui/addMessage", {
            content: msg,
            date: new Date()
          })
        })
      }, 100)
    },
    next() {
      let self = this
      this.$store.dispatch("queue/next").then(() => {
        self.$emit("next")
      })
    },
    previous() {
      let self = this
      this.$store.dispatch("queue/previous").then(() => {
        self.$emit("previous")
      })
    },
    handleError({ sound, error }) {
      this.$store.commit("player/isLoadingAudio", false)
      this.$store.dispatch("player/trackErrored")
    },
    getSound (trackData) {
      let cached = this.getSoundFromCache(trackData)
      if (cached) {
        return cached.sound
      }
      let srcs = this.getSrcs(trackData)
      let self = this
      let sound = new Howl({
        src: srcs.map((s) => { return s.url }),
        format: srcs.map((s) => { return s.type }),
        autoplay: false,
        loop: false,
        html5: true,
        preload: true,
        volume: this.volume,
        onend: function () {
          self.ended()
        },
        onunlock: function () {
          if (self.$store.state.player.playing && self.sound) {
            self.soundId = self.sound.play(self.soundId)
          }
        },
        onload: function () {
          let sound = this
          let node = this._sounds[0]._node;
          node.addEventListener('progress', () => {
            if (sound != self.currentSound) {
              return
            }
            self.updateBuffer(node)
          })
        },
        onplay: function () {
          self.$store.commit('player/isLoadingAudio', false)
          self.$store.commit('player/resetErrorCount')
          self.$store.commit('player/errored', false)
          self.$store.commit('player/duration', this.duration())

        },
        onloaderror: function (sound, error) {
          self.removeFromCache(this)
          if (this != self.currentSound) {
            return
          }
          console.log('Error while playing:', sound, error)
          self.handleError({sound, error})
        },
      })
      this.addSoundToCache(sound, trackData)
      return sound
    },
    getSrcs: function (trackData) {
      let a = document.createElement('audio')
      let allowed = ['probably', 'maybe']
      let sources = trackData.uploads.filter(u => {
        let canPlay = a.canPlayType(u.mimetype)
        return allowed.indexOf(canPlay) > -1
      }).map(u => {
        return {
          type: u.extension,
          url: this.$store.getters['instance/absoluteUrl'](u.listen_url),
        }
      })
      a.remove()
      // We always add a transcoded MP3 src at the end
      // because transcoding is expensive, but we want browsers that do
      // not support other codecs to be able to play it :)
      sources.push({
        type: 'mp3',
        url: url.updateQueryString(
          this.$store.getters['instance/absoluteUrl'](trackData.listen_url),
          'to',
          'mp3'
        )
      })
      if (this.$store.state.auth.authenticated) {
        // we need to send the token directly in url
        // so authentication can be checked by the backend
        // because for audio files we cannot use the regular Authentication
        // header
        let param = "jwt"
        let value = this.$store.state.auth.token
        if (this.$store.state.auth.scopedTokens && this.$store.state.auth.scopedTokens.listen) {
          // used scoped tokens instead of JWT to reduce the attack surface if the token
          // is leaked
          param = "token"
          value = this.$store.state.auth.scopedTokens.listen
        }
        sources.forEach(e => {
          e.url = url.updateQueryString(e.url, param, value)
        })
      }
      return sources
    },

    updateBuffer (node) {
      // from https://github.com/goldfire/howler.js/issues/752#issuecomment-372083163
      let range = 0;
      let bf = node.buffered;
      let time = node.currentTime;
      try {
        while(!(bf.start(range) <= time && time <= bf.end(range))) {
          range += 1;
        }
      } catch (IndexSizeError) {
        return
      }
      let loadPercentage
      let start =  bf.start(range)
      let end =  bf.end(range)
      if (range === 0) {
        // easy case, no user-seek
        let loadStartPercentage = start / node.duration;
        let loadEndPercentage = end / node.duration;
        loadPercentage = loadEndPercentage - loadStartPercentage;
      } else {
        let loaded = end - start
        let remainingToLoad = node.duration - start
        // user seeked a specific position in the audio, our progress must be
        // computed based on the remaining portion of the track
        loadPercentage = loaded / remainingToLoad;
      }
      if (loadPercentage * 100 === this.bufferProgress) {
        return
      }
      this.$store.commit('player/bufferProgress', loadPercentage * 100)
    },
    updateProgress: function () {
      this.isUpdatingTime = true
      if (this.currentSound && this.currentSound.state() === 'loaded') {
        let t = this.currentSound.seek()
        let d = this.currentSound.duration()
        this.$store.dispatch('player/updateProgress', t)
        this.updateBuffer(this.currentSound._sounds[0]._node)
        let toPreload = this.$store.state.queue.tracks[this.currentIndex + 1]
        if (!this.nextTrackPreloaded && toPreload && !this.getSoundFromCache(toPreload) && (t > this.preloadDelay || d - t < 30)) {
          this.getSound(toPreload)
          this.nextTrackPreloaded = true
        }
        if (t > (d / 2)) {
          let onlyTrack = this.$store.state.queue.tracks.length === 1
          if (this.listeningRecorded != this.currentTrack) {
            this.listeningRecorded = this.currentTrack
            this.$store.dispatch('player/trackListened', this.currentTrack)
          }
        }
      }
    },
    seek (step) {
      if (step > 0) {
        // seek right
        if (this.currentTime + step < this.duration) {
        this.$store.dispatch('player/updateProgress', (this.currentTime + step))
        } else {
        this.next() // parenthesis where missing here
        }
      }
      else {
        // seek left
        let position = Math.max(this.currentTime + step, 0)
        this.$store.dispatch('player/updateProgress', position)
      }
    },
    seekForward () {
      this.seek (5)
    },
    seekBackward () {
      this.seek (-5)
    },
    observeProgress: function (enable) {
      let self = this
      if (enable) {
        if (self.progressInterval) {
          clearInterval(self.progressInterval)
        }
        self.progressInterval = setInterval(() => {
          self.updateProgress()
        }, 1000)
      } else {
        clearInterval(self.progressInterval)
      }
    },
    setCurrentTime (t) {
      if (t < 0 | t > this.duration) {
        return
      }
      if (!this.currentSound || !this.currentSound._sounds[0]) {
        return
      }
      if (t === this.currentSound.seek()) {
        return
      }
      if (t === 0) {
        this.updateProgressThrottled.cancel()
      }
      this.currentSound.seek(t)
    },
    ended: function () {
      let onlyTrack = this.$store.state.queue.tracks.length === 1
      if (this.looping === 1 || (onlyTrack && this.looping === 2)) {
        this.currentSound.seek(0)
        this.$store.dispatch('player/updateProgress', 0)
        this.soundId = this.currentSound.play(this.soundId)
      } else {
        this.$store.dispatch('player/trackEnded', this.currentTrack)
      }
    },
    getSoundFromCache (trackData) {
      return this.soundsCache.filter((d) => {
        if (d.track.id !== trackData.id) {
          return false
        }

        return true
      })[0]
    },
    addSoundToCache (sound, trackData) {
      let data = {
        date: new Date(),
        track: trackData,
        sound: sound
      }
      this.soundsCache.push(data)
      this.checkCache()
    },
    checkCache () {
      let self = this
      let toKeep = []
      _.reverse(this.soundsCache).forEach((e) => {
        if (toKeep.length < self.maxPreloaded) {
          toKeep.push(e)
        } else {
          let src = e.sound._src
          e.sound.unload()
        }
      })
      this.soundsCache = _.reverse(toKeep)
    },
    removeFromCache (sound) {
      let toKeep = []
      this.soundsCache.forEach((e) => {
        if (e.sound === sound) {
          e.sound.unload()
        } else {
          toKeep.push(e)
        }
      })
      this.soundsCache = toKeep
    },
    async loadSound (newValue, oldValue) {
      let trackData = newValue
      let oldSound = this.currentSound
      if (oldSound && trackData !== oldValue) {
        oldSound.stop(this.soundId)
        this.soundId = null
      }
      if (!trackData) {
        return
      }
      if (!this.isShuffling && trackData != oldValue) {
        trackData = await this.getTrackData(trackData)
        if (trackData === null) {
          this.handleError({})
        }
        this.currentSound = this.getSound(trackData)
        this.$store.commit('player/isLoadingAudio', true)
        this.soundId = this.currentSound.play()
        this.$store.commit('player/errored', false)
        this.$store.commit('player/playing', true)
        this.$store.dispatch('player/updateProgress', 0)
        this.observeProgress(true)
      }
    },
    toggleMobilePlayer () {
      if (['queue', 'player'].indexOf(this.$store.state.ui.queueFocused) > -1) {
        this.$store.commit('ui/queueFocused', null)
      } else {
        this.$store.commit('ui/queueFocused', 'player')
      }
    },
    switchTab () {
      if (this.$store.state.ui.queueFocused === 'player') {
        this.$store.commit('ui/queueFocused', 'queue')
      } else {
        this.$store.commit('ui/queueFocused', 'player')

      }
    },
    updateMetadata () {
      // If the session is playing as a PWA, populate the notification
      // with details from the track
      if (this.currentTrack && 'mediaSession' in navigator) {
        let metadata = {
          title: this.currentTrack.title,
          artist: this.currentTrack.artist.name,
        }
        if (this.currentTrack.album && this.currentTrack.album.cover) {
          metadata.album = this.currentTrack.album.title
          metadata.artwork = [
            { src: this.currentTrack.album.cover.urls.original, sizes: '96x96',   type: 'image/png' },
            { src: this.currentTrack.album.cover.urls.original, sizes: '128x128', type: 'image/png' },
            { src: this.currentTrack.album.cover.urls.original, sizes: '192x192', type: 'image/png' },
            { src: this.currentTrack.album.cover.urls.original, sizes: '256x256', type: 'image/png' },
            { src: this.currentTrack.album.cover.urls.original, sizes: '384x384', type: 'image/png' },
            { src: this.currentTrack.album.cover.urls.original, sizes: '512x512', type: 'image/png' },
          ]
        }
        navigator.mediaSession.metadata = new MediaMetadata(metadata)
      }
    }
  },
  computed: {
    ...mapState({
      currentIndex: state => state.queue.currentIndex,
      playing: state => state.player.playing,
      isLoadingAudio: state => state.player.isLoadingAudio,
      volume: state => state.player.volume,
      looping: state => state.player.looping,
      duration: state => state.player.duration,
      bufferProgress: state => state.player.bufferProgress,
      errored: state => state.player.errored,
      currentTime: state => state.player.currentTime,
      queue: state => state.queue
    }),
    ...mapGetters({
      currentTrack: "queue/currentTrack",
      hasNext: "queue/hasNext",
      hasPrevious: "queue/hasPrevious",
      emptyQueue: "queue/isEmpty",
      durationFormatted: "player/durationFormatted",
      currentTimeFormatted: "player/currentTimeFormatted",
      progress: "player/progress"
    }),
    updateProgressThrottled () {
      return _.throttle(this.updateProgress, 50)
    },
    labels() {
      let audioPlayer = this.$pgettext('Sidebar/Player/Hidden text', "Media player")
      let previous = this.$pgettext('Sidebar/Player/Icon.Tooltip', "Previous track")
      let play = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Play track")
      let pause = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Pause track")
      let next = this.$pgettext('Sidebar/Player/Icon.Tooltip', "Next track")
      let unmute = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Unmute")
      let mute = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Mute")
      let expandQueue = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Expand queue")
      let loopingDisabled = this.$pgettext('Sidebar/Player/Icon.Tooltip',
        "Looping disabled. Click to switch to single-track looping."
      )
      let loopingSingle = this.$pgettext('Sidebar/Player/Icon.Tooltip',
        "Looping on a single track. Click to switch to whole queue looping."
      )
      let loopingWhole = this.$pgettext('Sidebar/Player/Icon.Tooltip',
        "Looping on whole queue. Click to disable looping."
      )
      let shuffle = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Shuffle your queue")
      let clear = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Clear your queue")
      let addArtistContentFilter = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', 'Hide content from this artist…')
      return {
        audioPlayer,
        previous,
        play,
        pause,
        next,
        unmute,
        mute,
        loopingDisabled,
        loopingSingle,
        loopingWhole,
        shuffle,
        clear,
        expandQueue,
        addArtistContentFilter,
      }
    },
  },
  watch: {
    currentTrack: {
      async handler (newValue, oldValue) {
        if (newValue === oldValue) {
          return
        }
        this.nextTrackPreloaded = false
        clearTimeout(this.playTimeout)
        let self = this
        if (this.currentSound) {
          this.currentSound.pause()
        }
        this.$store.commit("player/isLoadingAudio", true)
        this.playTimeout = setTimeout(async () => {
          await self.loadSound(newValue, oldValue)
        }, 500);
        this.updateMetadata()
      },
      immediate: false
    },
    volume(newValue) {
      this.sliderVolume = newValue
      if (this.currentSound) {
        this.currentSound.volume(newValue)
      }
    },
    sliderVolume(newValue) {
      this.$store.commit("player/volume", newValue)
    },
    playing: async function (newValue) {
      if (this.currentSound) {
        if (newValue === true) {
          this.soundId = this.currentSound.play(this.soundId)
        } else {
          this.currentSound.pause(this.soundId)
        }
      } else {
        await this.loadSound(this.currentTrack, null)
      }

      this.observeProgress(newValue)
    },
    currentTime (newValue) {
      if (!this.isUpdatingTime) {
        this.setCurrentTime(newValue)
      }
      this.isUpdatingTime = false
    },
    emptyQueue (newValue) {
      if (newValue) {
        Howler.unload()
      }
    }
  }
}
</script>
