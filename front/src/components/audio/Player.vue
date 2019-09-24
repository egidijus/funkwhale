<template>
  <section class="ui inverted segment player-wrapper" :aria-label="labels.audioPlayer" :style="style">
    <div class="player">
      <div v-if="currentTrack" class="track-area ui unstackable items">
        <div class="ui inverted item">
          <div class="ui tiny image">
            <img ref="cover" @load="updateBackground" v-if="currentTrack.album.cover && currentTrack.album.cover.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.album.cover.medium_square_crop)">
            <img v-else src="../../assets/audio/default-cover.png">
          </div>
          <div class="middle aligned content">
            <router-link class="small header discrete link track" :to="{name: 'library.tracks.detail', params: {id: currentTrack.id }}">
              {{ currentTrack.title }}
            </router-link>
            <div class="meta">
              <router-link class="artist" :to="{name: 'library.artists.detail', params: {id: currentTrack.artist.id }}">
                {{ currentTrack.artist.name }}
              </router-link> /
              <router-link class="album" :to="{name: 'library.albums.detail', params: {id: currentTrack.album.id }}">
                {{ currentTrack.album.title }}
              </router-link>
            </div>
            <div class="description">
              <track-favorite-icon
                v-if="$store.state.auth.authenticated"
                :class="{'inverted': !$store.getters['favorites/isFavorite'](currentTrack.id)}"
                :track="currentTrack"></track-favorite-icon>
              <track-playlist-icon
                v-if="$store.state.auth.authenticated"
                :class="['inverted']"
                :track="currentTrack"></track-playlist-icon>
              <button
                v-if="$store.state.auth.authenticated"
                @click="$store.dispatch('moderation/hide', {type: 'artist', target: currentTrack.artist})"
                :class="['ui', 'really', 'basic', 'circular', 'inverted', 'icon', 'button']"
                :aria-label="labels.addArtistContentFilter"
                :title="labels.addArtistContentFilter">
                <i :class="['eye slash outline', 'basic', 'icon']"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="progress-area" v-if="currentTrack && !errored">
        <div class="ui grid">
          <div class="left floated four wide column">
            <p class="timer start" @click="setCurrentTime(0)">{{currentTimeFormatted}}</p>
          </div>

          <div v-if="!isLoadingAudio" class="right floated four wide column">
            <p class="timer total">{{durationFormatted}}</p>
          </div>
        </div>
        <div
          ref="progress"
          :class="['ui', 'small', 'orange', 'inverted', {'indicating': isLoadingAudio}, 'progress']"
          @click="touchProgress">
          <div class="buffer bar" :data-percent="bufferProgress" :style="{ 'width': bufferProgress + '%' }"></div>
          <div class="position bar" :data-percent="progress" :style="{ 'width': progress + '%' }"></div>
        </div>
      </div>
      <div class="ui small warning message" v-if="currentTrack && errored">
        <div class="header">
          <translate translate-context="Sidebar/Player/Error message.Title">The track cannot be loaded</translate>
        </div>
        <p v-if="hasNext && playing && $store.state.player.errorCount < $store.state.player.maxConsecutiveErrors">
          <translate translate-context="Sidebar/Player/Error message.Paragraph">The next track will play automatically in a few seconds…</translate>
          <i class="loading spinner icon"></i>
        </p>
        <p>
          <translate translate-context="Sidebar/Player/Error message.Paragraph">You may have a connectivity issue.</translate>
        </p>
      </div>
      <div class="two wide column controls ui grid">
        <span
          role="button"
          :title="labels.previousTrack"
          :aria-label="labels.previousTrack"
          class="two wide column control"
          @click.prevent.stop="previous"
          :disabled="emptyQueue">
            <i :class="['ui', 'backward step', {'disabled': emptyQueue}, 'icon']"></i>
        </span>
        <span
          role="button"
          v-if="!playing"
          :title="labels.play"
          :aria-label="labels.play"
          @click.prevent.stop="togglePlay"
          class="two wide column control">
            <i :class="['ui', 'play', {'disabled': !currentTrack}, 'icon']"></i>
        </span>
        <span
          role="button"
          v-else
          :title="labels.pause"
          :aria-label="labels.pause"
          @click.prevent.stop="togglePlay"
          class="two wide column control">
            <i :class="['ui', 'pause', {'disabled': !currentTrack}, 'icon']"></i>
        </span>
        <span
          role="button"
          :title="labels.next"
          :aria-label="labels.next"
          class="two wide column control"
          @click.prevent.stop="next"
          :disabled="!hasNext">
            <i :class="['ui', {'disabled': !hasNext}, 'forward step', 'icon']" ></i>
        </span>
        <div
          class="wide column control volume-control"
          v-on:mouseover="showVolume = true"
          v-on:mouseleave="showVolume = false"
          v-bind:class="{ active : showVolume }">
          <span
            role="button"
            v-if="volume === 0"
            :title="labels.unmute"
            :aria-label="labels.unmute"
            @click.prevent.stop="unmute">
            <i class="volume off icon"></i>
          </span>
          <span
            role="button"
            v-else-if="volume < 0.5"
            :title="labels.mute"
            :aria-label="labels.mute"
            @click.prevent.stop="mute">
            <i class="volume down icon"></i>
          </span>
          <span
            role="button"
            v-else
            :title="labels.mute"
            :aria-label="labels.mute"
            @click.prevent.stop="mute">
            <i class="volume up icon"></i>
          </span>
          <input
            type="range"
            step="0.05"
            min="0"
            max="1"
            v-model="sliderVolume"
            v-if="showVolume" />
        </div>
        <div class="two wide column control looping" v-if="!showVolume">
          <span
            role="button"
            v-if="looping === 0"
            :title="labels.loopingDisabled"
            :aria-label="labels.loopingDisabled"
            @click.prevent.stop="$store.commit('player/looping', 1)"
            :disabled="!currentTrack">
            <i :class="['ui', {'disabled': !currentTrack}, 'step', 'repeat', 'icon']"></i>
          </span>
          <span
            role="button"
            @click.prevent.stop="$store.commit('player/looping', 2)"
            :title="labels.loopingSingle"
            :aria-label="labels.loopingSingle"
            v-if="looping === 1"
            :disabled="!currentTrack">
            <i
              class="repeat icon">
              <span class="ui circular tiny orange label">1</span>
            </i>
          </span>
          <span
            role="button"
            :title="labels.loopingWhole"
            :aria-label="labels.loopingWhole"
            v-if="looping === 2"
            :disabled="!currentTrack"
            @click.prevent.stop="$store.commit('player/looping', 0)">
            <i
              class="repeat orange icon">
            </i>
          </span>
        </div>
        <span
          role="button"
          :disabled="queue.tracks.length === 0"
          :title="labels.shuffle"
          :aria-label="labels.shuffle"
          v-if="!showVolume"
          @click.prevent.stop="shuffle()"
          class="two wide column control">
          <div v-if="isShuffling" class="ui inline shuffling inverted tiny active loader"></div>
          <i v-else :class="['ui', 'random', {'disabled': queue.tracks.length === 0}, 'icon']" ></i>
        </span>
        <div class="one wide column" v-if="!showVolume"></div>
        <span
          role="button"
          :disabled="queue.tracks.length === 0"
          :title="labels.clear"
          :aria-label="labels.clear"
          v-if="!showVolume"
          @click.prevent.stop="clean()"
          class="two wide column control">
          <i class="icons">
            <i :class="['ui', 'trash', {'disabled': queue.tracks.length === 0}, 'icon']" ></i>
            <i :class="['ui corner inverted', 'list', {'disabled': queue.tracks.length === 0}, 'icon']" ></i>
          </i>
        </span>
      </div>
      <GlobalEvents
        @keydown.space.prevent.exact="togglePlay"
        @keydown.ctrl.shift.left.prevent.exact="previous"
        @keydown.ctrl.shift.right.prevent.exact="next"
        @keydown.shift.down.prevent.exact="$store.commit('player/incrementVolume', -0.1)"
        @keydown.shift.up.prevent.exact="$store.commit('player/incrementVolume', 0.1)"
        @keydown.right.prevent.exact="seek (5)"
        @keydown.left.prevent.exact="seek (-5)"
        @keydown.shift.right.prevent.exact="seek (30)"
        @keydown.shift.left.prevent.exact="seek (-30)"
        @keydown.m.prevent.exact="toggleMute"
        @keydown.l.prevent.exact="$store.commit('player/toggleLooping')"
        @keydown.s.prevent.exact="shuffle"
        @keydown.f.prevent.exact="$store.dispatch('favorites/toggle', currentTrack.id)"
        @keydown.q.prevent.exact="clean"
        />
    </div>
  </section>
</template>

<script>
import { mapState, mapGetters, mapActions } from "vuex"
import GlobalEvents from "@/components/utils/global-events"
import ColorThief from "@/vendor/color-thief"
import { Howl } from "howler"
import $ from 'jquery'
import _ from '@/lodash'
import url from '@/utils/url'
import axios from 'axios'

import TrackFavoriteIcon from "@/components/favorites/TrackFavoriteIcon"
import TrackPlaylistIcon from "@/components/playlists/TrackPlaylistIcon"

export default {
  components: {
    TrackFavoriteIcon,
    TrackPlaylistIcon,
    GlobalEvents,
  },
  data() {
    let defaultAmbiantColors = [
      [46, 46, 46],
      [46, 46, 46],
      [46, 46, 46],
      [46, 46, 46]
    ]
    return {
      isShuffling: false,
      sliderVolume: this.volume,
      defaultAmbiantColors: defaultAmbiantColors,
      showVolume: false,
      ambiantColors: defaultAmbiantColors,
      currentSound: null,
      dummyAudio: null,
      isUpdatingTime: false,
      sourceErrors: 0,
      progressInterval: null,
      maxPreloaded: 3,
      preloadDelay: 15,
      soundsCache: [],
      soundId: null,
      playTimeout: null,
      nextTrackPreloaded: false,
      nowPlayingTimeout: null,
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
    touchProgress(e) {
      let time
      let target = this.$refs.progress
      time = (e.layerX / target.offsetWidth) * this.duration
      this.setCurrentTime(time)
    },
    updateBackground() {
      // delete existing canvas, if any
      $('canvas.color-thief').remove()
      if (!this.currentTrack.album.cover) {
        this.ambiantColors = this.defaultAmbiantColors
        return
      }
      let image = this.$refs.cover
      try {
        this.ambiantColors = ColorThief.prototype.getPalette(image, 4).slice(0, 4)
      } catch (e) {
        console.log('Cannot generate player background from cover image, likely a cross-origin tainted canvas issue')
      }
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
          if (self.$store.state.player.playing) {
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
          if (trackData.id === self.currentTrack.id) {
            self.nowPlayingTimeout = setTimeout(() => {
              self.$store.dispatch('player/nowPlaying', trackData)
            }, 5000)
          }
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
      let sources = trackData.uploads.map(u => {
        return {
          type: u.extension,
          url: this.$store.getters['instance/absoluteUrl'](u.listen_url),
        }
      })
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
        sources.forEach(e => {
          e.url = url.updateQueryString(e.url, 'jwt', this.$store.state.auth.token)
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
        if (this.playing) {
          this.soundId = this.currentSound.play()
          this.$store.commit('player/errored', false)
          this.$store.commit('player/playing', true)
          this.$store.dispatch('player/updateProgress', 0)
          this.observeProgress(true)
        }
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
      emptyQueue: "queue/isEmpty",
      durationFormatted: "player/durationFormatted",
      currentTimeFormatted: "player/currentTimeFormatted",
      progress: "player/progress"
    }),
    updateProgressThrottled () {
      return _.throttle(this.updateProgress, 250)
    },
    labels() {
      let audioPlayer = this.$pgettext('Sidebar/Player/Hidden text', "Media player")
      let previousTrack = this.$pgettext('Sidebar/Player/Icon.Tooltip', "Previous track")
      let play = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Play track")
      let pause = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Pause track")
      let next = this.$pgettext('Sidebar/Player/Icon.Tooltip', "Next track")
      let unmute = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Unmute")
      let mute = this.$pgettext('Sidebar/Player/Icon.Tooltip/Verb', "Mute")
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
        previousTrack,
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
        addArtistContentFilter,
      }
    },
    style: function() {
      let style = {
        background: this.ambiantGradiant
      }
      return style
    },
    ambiantGradiant: function() {
      let indexConf = [
        { orientation: 330, percent: 100, opacity: 0.7 },
        { orientation: 240, percent: 90, opacity: 0.7 },
        { orientation: 150, percent: 80, opacity: 0.7 },
        { orientation: 60, percent: 70, opacity: 0.7 }
      ]
      let gradients = this.ambiantColors
        .map((e, i) => {
          let [r, g, b] = e
          let conf = indexConf[i]
          return `linear-gradient(${
            conf.orientation
          }deg, rgba(${r}, ${g}, ${b}, ${
            conf.opacity
          }) 10%, rgba(255, 255, 255, 0) ${conf.percent}%)`
        })
        .join(", ")
      return gradients
    },
  },
  watch: {
    currentTrack: {
      async handler (newValue, oldValue) {
        if (this.nowPlayingTimeout) {
          clearTimeout(this.nowPlayingTimeout)
        }
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
          if (!newValue || !newValue.album.cover) {
            self.ambiantColors = self.defaultAmbiantColors
          }
        }, 500);
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
          if (this.nowPlayingTimeout) {
            clearTimeout(this.nowPlayingTimeout)
          }
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

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
.ui.progress {
  margin: 0.5rem 0 1rem;
}
.progress {
  cursor: pointer;
  .bar {
    min-width: 0 !important;
  }
}

.ui.inverted.item > .content > .description {
  color: rgba(255, 255, 255, 0.9) !important;
}

.ui.item {
  .meta {
    font-size: 90%;
    line-height: 1.2;
  }
}
.timer.total {
  text-align: right;
}
.timer.start {
  cursor: pointer;
}
.track-area {
  margin-top: 0;
  .header,
  .meta,
  .artist,
  .album {
    color: white !important;
  }
}
.controls a {
  color: white;
}

.controls .icon.big {
  cursor: pointer;
  font-size: 2em !important;
}

.controls .icon {
  cursor: pointer;
  vertical-align: middle;
}

.control .icon {
  font-size: 1.5em;
}
.progress-area .actions {
  text-align: center;
}
.ui.progress:not([data-percent]):not(.indeterminate)
  .bar.position:not(.buffer) {
  background: #ff851b;
}
.volume-control {
  position: relative;
  width: 12.5% !important;
  [type="range"] {
    max-width: 70%;
    position: absolute;
    bottom: 1.1rem;
    left: 25%;
    cursor: pointer;
    background-color: transparent;
  }
  input[type="range"]:focus {
    outline: none;
  }
  input[type="range"]::-webkit-slider-runnable-track {
    cursor: pointer;
  }
  input[type="range"]::-webkit-slider-thumb {
    background: white;
    cursor: pointer;
    -webkit-appearance: none;
    border-radius: 3px;
    width: 10px;
  }
  input[type="range"]::-moz-range-track {
    cursor: pointer;
    background: white;
    opacity: 0.3;
  }
  input[type="range"]::-moz-focus-outer {
    border: 0;
  }
  input[type="range"]::-moz-range-thumb {
    background: white;
    cursor: pointer;
    border-radius: 3px;
    width: 10px;
  }
  input[type="range"]::-ms-track {
    cursor: pointer;
    background: transparent;
    border-color: transparent;
    color: transparent;
  }
  input[type="range"]::-ms-fill-lower {
    background: white;
    opacity: 0.3;
  }
  input[type="range"]::-ms-fill-upper {
    background: white;
    opacity: 0.3;
  }
  input[type="range"]::-ms-thumb {
    background: white;
    cursor: pointer;
    border-radius: 3px;
    width: 10px;
  }
  input[type="range"]:focus::-ms-fill-lower {
    background: white;
  }
  input[type="range"]:focus::-ms-fill-upper {
    background: white;
  }
}

.active.volume-control {
  width: 60% !important;
}

.looping.control {
  i {
    position: relative;
  }
  .label {
    position: absolute;
    font-size: 0.7rem;
    bottom: -0.7rem;
    right: -0.7rem;
  }
}
.ui.feed.icon {
  margin: 0;
}
.shuffling.loader.inline {
  margin: 0;
}

@keyframes MOVE-BG {
  from {
    transform: translateX(0px);
  }
  to {
    transform: translateX(46px);
  }
}

.indicating.progress {
  overflow: hidden;
}

.ui.progress .bar {
  transition: none;
}

.ui.inverted.progress .buffer.bar {
  position: absolute;
  background-color: rgba(255, 255, 255, 0.15);
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

.icons {
  position: absolute;
}

i.icons .corner.icon {
  font-size: 1em;
  right: -0.3em;
}
</style>
