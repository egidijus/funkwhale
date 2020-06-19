<template>
  <section class="main with-background component-queue" :aria-label="labels.queue">
    <div :class="['ui vertical stripe queue segment', playerFocused ? 'player-focused' : '']">
      <div class="ui fluid container">
        <div class="ui stackable grid" id="queue-grid">
          <div class="ui six wide column current-track">
            <div class="ui basic segment" id="player">
              <template v-if="currentTrack">
                <img ref="cover" v-if="currentTrack.cover && currentTrack.cover.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.cover.medium_square_crop)">
                <img ref="cover" v-else-if="currentTrack.album && currentTrack.album.cover && currentTrack.album.cover.original" :src="$store.getters['instance/absoluteUrl'](currentTrack.album.cover.medium_square_crop)">
                <img class="ui image" v-else src="../assets/audio/default-cover.png">
                <h1 class="ui header">
                  <div class="content">
                    <router-link class="small header discrete link track" :title="currentTrack.title" :to="{name: 'library.tracks.detail', params: {id: currentTrack.id }}">
                      {{ currentTrack.title | truncate(35) }}
                    </router-link>
                    <div class="sub header">
                      <router-link class="discrete link artist" :title="currentTrack.artist.name" :to="{name: 'library.artists.detail', params: {id: currentTrack.artist.id }}">
                        {{ currentTrack.artist.name | truncate(35) }}</router-link> <template v-if="currentTrack.album">/<router-link class="discrete link album" :title="currentTrack.album.title" :to="{name: 'library.albums.detail', params: {id: currentTrack.album.id }}">
                        {{ currentTrack.album.title | truncate(35) }}
                      </router-link></template>
                    </div>
                  </div>
                </h1>
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
                <div class="additional-controls">
                  <track-favorite-icon
                    class="tablet-and-below"
                    v-if="$store.state.auth.authenticated"
                    :track="currentTrack"></track-favorite-icon>
                  <track-playlist-icon
                    class="tablet-and-below"
                    v-if="$store.state.auth.authenticated"
                    :track="currentTrack"></track-playlist-icon>
                  <button
                    v-if="$store.state.auth.authenticated"
                    @click="$store.dispatch('moderation/hide', {type: 'artist', target: currentTrack.artist})"
                    :class="['ui', 'really', 'basic', 'circular', 'icon', 'button', 'tablet-and-below']"
                    :aria-label="labels.addArtistContentFilter"
                    :title="labels.addArtistContentFilter">
                    <i :class="['eye slash outline', 'basic', 'icon']"></i>
                  </button>
                </div>
                <div class="progress-wrapper">
                  <div class="progress-area" v-if="currentTrack && !errored">
                    <div
                      ref="progress"
                      :class="['ui', 'small', 'vibrant', {'indicating': isLoadingAudio}, 'progress']"
                      @click="touchProgress">
                      <div class="buffer bar" :data-percent="bufferProgress" :style="{ 'width': bufferProgress + '%' }"></div>
                      <div class="position bar" :data-percent="progress" :style="{ 'width': progress + '%' }"></div>
                    </div>
                  </div>
                  <div class="progress-area" v-else>
                    <div
                      ref="progress"
                      :class="['ui', 'small', 'vibrant', 'progress']">
                      <div class="buffer bar"></div>
                      <div class="position bar"></div>
                    </div>
                  </div>
                  <div class="progress">
                    <template v-if="!isLoadingAudio">
                      <span role="button" class="left floated timer start" @click="setCurrentTime(0)">{{currentTimeFormatted}}</span>
                      <span class="right floated timer total">{{durationFormatted}}</span>
                    </template>
                    <template v-else>
                      <span class="left floated timer">00:00</span>
                      <span class="right floated timer">00:00</span>
                    </template>
                  </div>
                </div>
                <div class="player-controls tablet-and-below">
                  <template>
                    <span
                      role="button"
                      :title="labels.previousTrack"
                      :aria-label="labels.previousTrack"
                      class="control"
                      @click.prevent.stop="$store.dispatch('queue/previous')"
                      :disabled="emptyQueue">
                        <i :class="['ui', 'backward step', {'disabled': emptyQueue}, 'icon']"></i>
                    </span>

                    <span
                      role="button"
                      v-if="!playing"
                      :title="labels.play"
                      :aria-label="labels.play"
                      @click.prevent.stop="togglePlay"
                      class="control">
                        <i :class="['ui', 'play', {'disabled': !currentTrack}, 'icon']"></i>
                    </span>
                    <span
                      role="button"
                      v-else
                      :title="labels.pause"
                      :aria-label="labels.pause"
                      @click.prevent.stop="togglePlay"
                      class="control">
                        <i :class="['ui', 'pause', {'disabled': !currentTrack}, 'icon']"></i>
                    </span>
                    <span
                      role="button"
                      :title="labels.next"
                      :aria-label="labels.next"
                      class="control"
                      @click.prevent.stop="$store.dispatch('queue/next')"
                      :disabled="!hasNext">
                        <i :class="['ui', {'disabled': !hasNext}, 'forward step', 'icon']" ></i>
                    </span>
                  </template>
                </div>
              </template>
            </div>
          </div>
          <div class="ui ten wide column queue-column">
            <div class="ui basic clearing fixed-header segment">
              <h2 class="ui header">
                <div class="content">
                  <button
                    class="ui right floated basic icon button"
                    @click="$store.dispatch('queue/clean')">
                      <translate translate-context="*/Queue/*/Verb">Clear</translate>
                  </button>
                  {{ labels.queue }}
                  <div class="sub header">
                    <div>
                      <translate translate-context="Sidebar/Queue/Text" :translate-params="{index: queue.currentIndex + 1, length: queue.tracks.length}">
                        Track %{ index } of %{ length }
                      </translate><template v-if="!$store.state.radios.running"> -
                        <span :title="labels.duration">
                          {{ timeLeft }}
                        </span>
                      </template>
                    </div>
                  </div>
                </div>
              </h2>
            </div>
            <table class="ui compact very basic fixed single line selectable unstackable table">
              <draggable v-model="tracks" tag="tbody" @update="reorder" handle=".handle">
                <tr
                  v-for="(track, index) in tracks"
                  :key="index"
                  :class="['queue-item', {'active': index === queue.currentIndex}]">
                  <td class="handle">
                    <i class="grip lines icon"></i>
                  </td>
                  <td class="image-cell" @click="$store.dispatch('queue/currentIndex', index)">
                    <img class="ui mini image" v-if="track.cover && track.cover.original" :src="$store.getters['instance/absoluteUrl'](track.cover.medium_square_crop)">
                    <img class="ui mini image" v-else-if="track.album && track.album.cover && track.album.cover.original" :src="$store.getters['instance/absoluteUrl'](track.album.cover.medium_square_crop)">
                    <img class="ui mini image" v-else src="../assets/audio/default-cover.png">
                  </td>
                  <td colspan="3" @click="$store.dispatch('queue/currentIndex', index)">
                    <button class="title reset ellipsis" :title="track.title" :aria-label="labels.selectTrack">
                      <strong>{{ track.title }}</strong><br />
                      <span>
                        {{ track.artist.name }}
                      </span>
                    </button>
                  </td>
                  <td class="duration-cell">
                    <template v-if="track.uploads.length > 0">
                      {{ time.durationFormatted(track.uploads[0].duration) }}
                    </template>
                  </td>
                  <td class="controls">
                    <template v-if="$store.getters['favorites/isFavorite'](track.id)">
                      <i class="pink heart icon"></i>
                    </template>
                    <button :title="labels.removeFromQueue" @click.stop="cleanTrack(index)" :class="['ui', 'really', 'tiny', 'basic', 'circular', 'icon', 'button']">
                      <i class="x icon"></i>
                    </button>
                  </td>
                </tr>
              </draggable>
            </table>

            <div v-if="$store.state.radios.running" class="ui info message">
              <div class="content">
                <div class="header">
                  <i class="feed icon"></i> <translate translate-context="Sidebar/Player/Title">You have a radio playing</translate>
                </div>
                <p><translate translate-context="Sidebar/Player/Paragraph">New tracks will be appended here automatically.</translate></p>
                <div @click="$store.dispatch('radios/stop')" class="ui basic primary button"><translate translate-context="*/Player/Button.Label/Short, Verb">Stop radio</translate></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script>
import { mapState, mapGetters, mapActions } from "vuex"
import $ from 'jquery'
import moment from "moment"
import lodash from '@/lodash'
import time from "@/utils/time"

import store from "@/store"

export default {
  components: {
    TrackFavoriteIcon:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/favorites/TrackFavoriteIcon"),
    TrackPlaylistIcon:  () => import(/* webpackChunkName: "auth-audio" */ "@/components/playlists/TrackPlaylistIcon"),
    VolumeControl:  () => import(/* webpackChunkName: "audio" */ "@/components/audio/VolumeControl"),
    draggable:  () => import(/* webpackChunkName: "draggable" */ "vuedraggable"),
  },
  data () {
    return {
      showVolume: false,
      isShuffling: false,
      tracksChangeBuffer: null,
      time
    }
  },
  mounted () {
    let self = this
    this.$nextTick(() => {
      setTimeout(() => {
        this.scrollToCurrent()
        // delay is to let transition work
      }, 400);
    })
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
    tracks: {
      get() {
        return this.$store.state.queue.tracks
      },
      set(value) {
        this.tracksChangeBuffer = value
      }
    },
    labels () {
      return {
        queue: this.$pgettext('*/*/*', 'Queue'),
        duration: this.$pgettext('*/*/*', 'Duration'),
      }
    },
    timeLeft () {
      let seconds = lodash.sum(
        this.queue.tracks.slice(this.queue.currentIndex).map((t) => {
          return (t.uploads || []).map((u) => {
            return u.duration || 0
          })[0] || 0
        })
      )
      return moment(this.$store.state.ui.lastDate).add(seconds, 'seconds').fromNow(true)
    },
    sliderVolume: {
      get () {
        return this.volume
      },
      set (v) {
        this.$store.commit("player/volume", v)
      }
    },
    playerFocused () {
      return this.$store.state.ui.queueFocused === 'player'
    }
  },
  methods: {
    ...mapActions({
      cleanTrack: "queue/cleanTrack",
      mute: "player/mute",
      unmute: "player/unmute",
      clean: "queue/clean",
      toggleMute: "player/toggleMute",
      togglePlay: "player/togglePlay",
    }),
    reorder: function(event) {
      this.$store.commit("queue/reorder", {
        tracks: this.tracksChangeBuffer,
        oldIndex: event.oldIndex,
        newIndex: event.newIndex
      })
    },
    scrollToCurrent() {
      let current = $(this.$el).find('.queue-item.active')[0]
      if (!current) {
        return
      }
      const elementRect = current.getBoundingClientRect();
      const absoluteElementTop = elementRect.top + window.pageYOffset;
      const middle = absoluteElementTop - (window.innerHeight / 2);
      window.scrollTo({top: middle, behaviour: 'smooth'});
    },
    touchProgress(e) {
      let time
      let target = this.$refs.progress
      time = (e.layerX / target.offsetWidth) * this.duration
      this.$emit('touch-progress', time)
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
  },
  watch: {
    "$store.state.ui.queueFocused": {
      handler (v) {
        if (v === 'queue') {
          this.$nextTick(() => {
            this.scrollToCurrent()
          })
        }
      },
      immediate: true
    },
    '$store.state.queue.currentIndex': {
      handler () {
        this.$nextTick(() => {
          this.scrollToCurrent()
        })
      },
    },
    '$store.state.queue.tracks': {
      handler (v) {
        if (!v || v.length === 0) {
          this.$store.commit('ui/queueFocused', null)
        }
      },
      immediate: true
    },
    "$route.fullPath" () {
      this.$store.commit('ui/queueFocused', null)
    }
  }
}
</script>
