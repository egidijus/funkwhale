<template>
  <span :title="title" :class="['ui', {'tiny': discrete}, {'icon': !discrete}, {'buttons': !dropdownOnly && !iconOnly}, 'play-button component-play-button']">
    <button
      v-if="!dropdownOnly"
      @click.stop.prevent="replacePlay"
      :disabled="!playable"
      :aria-label="labels.replacePlay"
      :class="buttonClasses.concat(['ui', {loading: isLoading}, {'mini': discrete}, {disabled: !playable}])">
      <i :class="[playIconClass, 'icon']"></i>
      <template v-if="!discrete && !iconOnly">&nbsp;<slot><translate translate-context="*/Queue/Button.Label/Short, Verb">Play</translate></slot></template>
    </button>
    <div
      v-if="!discrete && !iconOnly"
      @click.prevent="clicked = true"
      role="button"
      :class="['ui', {disabled: !playable && !filterableArtist}, 'floating', 'dropdown', {'icon': !dropdownOnly}, {'button': !dropdownOnly}]">
      <i :class="dropdownIconClasses.concat(['icon'])" :title="title" ></i>
      <div class="menu" v-if="clicked">
        <button class="item basic" ref="add" data-ref="add" :disabled="!playable" @click.stop.prevent="add" :title="labels.addToQueue">
          <i class="plus icon"></i><translate translate-context="*/Queue/Dropdown/Button/Label/Short">Add to queue</translate>
        </button>
        <button class="item basic" ref="addNext" data-ref="addNext" :disabled="!playable" @click.stop.prevent="addNext()" :title="labels.playNext">
          <i class="step forward icon"></i>{{ labels.playNext }}
        </button>
        <button class="item basic" ref="playNow" data-ref="playNow" :disabled="!playable" @click.stop.prevent="addNext(true)" :title="labels.playNow">
          <i class="play icon"></i>{{ labels.playNow }}
        </button>
        <button v-if="track" class="item basic" :disabled="!playable" @click.stop.prevent="$store.dispatch('radios/start', {type: 'similar', objectId: track.id})" :title="labels.startRadio">
          <i class="feed icon"></i><translate translate-context="*/Queue/Button.Label/Short, Verb">Start radio</translate>
        </button>
        <div class="divider"></div>
        <button v-if="filterableArtist" class="item basic" :disabled="!filterableArtist" @click.stop.prevent="filterArtist" :title="labels.hideArtist">
          <i class="eye slash outline icon"></i><translate translate-context="*/Queue/Dropdown/Button/Label/Short">Hide content from this artist</translate>
        </button>
        <button
          v-for="obj in getReportableObjs({track, album, artist, playlist, account, channel})"
          :key="obj.target.type + obj.target.id"
          class="item basic"
          @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
          <i class="share icon" /> {{ obj.label }}
        </button>
      </div>
    </div>
  </span>
</template>

<script>
import axios from 'axios'
import jQuery from 'jquery'

import ReportMixin from '@/components/mixins/Report'

export default {
  mixins: [ReportMixin],
  props: {
    // we can either have a single or multiple tracks to play when clicked
    tracks: {type: Array, required: false},
    track: {type: Object, required: false},
    account: {type: Object, required: false},
    dropdownIconClasses: {type: Array, required: false, default: () => { return ['dropdown'] }},
    playIconClass: {type: String, required: false, default: 'play icon'},
    buttonClasses: {type: Array, required: false, default: () => { return ['button'] }},
    playlist: {type: Object, required: false},
    discrete: {type: Boolean, default: false},
    dropdownOnly: {type: Boolean, default: false},
    iconOnly: {type: Boolean, default: false},
    artist: {type: Object, required: false},
    album: {type: Object, required: false},
    library: {type: Object, required: false},
    channel: {type: Object, required: false},
    isPlayable: {type: Boolean, required: false, default: null}
  },
  data () {
    return {
      isLoading: false,
      clicked: false
    }
  },
  computed: {
    labels () {
      let replacePlay
      if (this.track) {
        replacePlay = this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play track')
      } else if (this.album) {
        replacePlay = this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play album')
      } else if (this.artist) {
        replacePlay = this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play artist')
      } else if (this.playlist) {
        replacePlay = this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play playlist')
      } else {
        replacePlay = this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play tracks')
      }
      
      return {
        playNow: this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play now'),
        addToQueue: this.$pgettext('*/Queue/Dropdown/Button/Title', 'Add to current queue'),
        playNext: this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play next'),
        startRadio: this.$pgettext('*/Queue/Dropdown/Button/Title', 'Play similar songs'),
        report: this.$pgettext('*/Moderation/*/Button/Label,Verb', 'Report…'),
        replacePlay,
      }
    },
    title () {
      if (this.playable) {
        return this.$pgettext('*/*/Button.Label/Noun', 'More…')
      } else {
        if (this.track) {
          return this.$pgettext('*/Queue/Button/Title', 'This track is not available in any library you have access to')
        }
      }
    },
    playable () {
      if (this.isPlayable) {
        return true
      }
      if (this.track) {
        return this.track.uploads && this.track.uploads.length > 0
      } else if (this.artist && this.artist.tracks_count) {
        return this.artist.tracks_count > 0
      } else if (this.artist && this.artist.albums) {
        return this.artist.albums.filter((a) => {
          return a.is_playable === true
        }).length > 0
      } else if (this.album) {
        return true
      } else if (this.tracks) {
        return this.tracks.filter((t) => {
          return t.uploads && t.uploads.length > 0
        }).length > 0
      }
      return false
    },
    filterableArtist () {
      if (this.track) {
        return this.track.artist
      }
      if (this.album) {
        return this.album.artist
      }
      if (this.artist) {
        return this.artist
      }
    },
  },
  methods: {

    filterArtist () {
      this.$store.dispatch('moderation/hide', {type: 'artist', target: this.filterableArtist})
    },
    getTracksPage (page, params, resolve, tracks) {
      if (page > 10) {
        // it's 10 * 100 tracks already, let's stop here
        resolve(tracks)
      }
      // when fetching artists/or album tracks, sometimes, we may have to fetch
      // multiple pages
      let self = this
      params['page_size'] = 100
      params['page'] = page
      params['hidden'] = ''
      params['playable'] = 'true'
      tracks = tracks || []
      axios.get('tracks/', {params: params}).then((response) => {
        response.data.results.forEach(t => {
          tracks.push(t)
        })
        if (response.data.next) {
          self.getTracksPage(page + 1, params, resolve, tracks)
        } else {
          resolve(tracks)
        }
      })
    },
    getPlayableTracks () {
      let self = this
      this.isLoading = true
      let getTracks = new Promise((resolve, reject) => {
        if (self.track) {
          if (!self.track.uploads || self.track.uploads.length === 0) {
            // fetch uploads from api
            axios.get(`tracks/${self.track.id}/`).then((response) => {
              resolve([response.data])
            })
          } else {
            resolve([self.track])
          }
        } else if (self.tracks) {
          resolve(self.tracks)
        } else if (self.playlist) {
          let url = 'playlists/' + self.playlist.id + '/'
          axios.get(url + 'tracks/').then((response) => {
            let artistIds = self.$store.getters['moderation/artistFilters']().map((f) => {
              return f.target.id
            })
            let tracks = response.data.results.map(plt => {
              return plt.track
            })
            if (artistIds.length > 0) {
              // skip tracks from hidden artists
              tracks = tracks.filter((t) => {
                let matchArtist = artistIds.indexOf(t.artist.id) > -1
                return !(matchArtist || t.album && artistIds.indexOf(t.album.artist.id) > -1)
              })
            }

            resolve(tracks)
          })
        } else if (self.artist) {
          let params = {'artist': self.artist.id, include_channels: 'true', 'ordering': 'album__release_date,disc_number,position'}
          self.getTracksPage(1, params, resolve)
        } else if (self.album) {
          let params = {'album': self.album.id, include_channels: 'true', 'ordering': 'disc_number,position'}
          self.getTracksPage(1, params, resolve)
        } else if (self.library) {
          let params = {'library': self.library.uuid, 'ordering': '-creation_date'}
          self.getTracksPage(1, params, resolve)
        }
      })
      return getTracks.then((tracks) => {
        setTimeout(e => {
          self.isLoading = false
        }, 250)
        return tracks.filter(e => {
          return e.uploads && e.uploads.length > 0
        })
      })
    },
    add () {
      let self = this
      this.getPlayableTracks().then((tracks) => {
        self.$store.dispatch('queue/appendMany', {tracks: tracks}).then(() => self.addMessage(tracks))
      })
      jQuery(self.$el).find('.ui.dropdown').dropdown('hide')
    },
    replacePlay () {
      let self = this
      self.$store.dispatch('queue/clean')
      this.getPlayableTracks().then((tracks) => {
        self.$store.dispatch('queue/appendMany', {tracks: tracks}).then(() => self.addMessage(tracks))
      })
      jQuery(self.$el).find('.ui.dropdown').dropdown('hide')
    },
    addNext (next) {
      let self = this
      let wasEmpty = this.$store.state.queue.tracks.length === 0
      this.getPlayableTracks().then((tracks) => {
        self.$store.dispatch('queue/appendMany', {tracks: tracks, index: self.$store.state.queue.currentIndex + 1}).then(() => self.addMessage(tracks))
        let goNext = next && !wasEmpty
        if (goNext) {
          self.$store.dispatch('queue/next')
        }
      })
      jQuery(self.$el).find('.ui.dropdown').dropdown('hide')
    },
    addMessage (tracks) {
      if (tracks.length < 1) {
        return
      }
      let msg = this.$npgettext('*/Queue/Message', '%{ count } track was added to your queue', '%{ count } tracks were added to your queue', tracks.length)
      this.$store.commit('ui/addMessage', {
        content: this.$gettextInterpolate(msg, {count: tracks.length}),
        date: new Date()
      })
    },
  },
  watch: {
    clicked () {
      let self = this
      this.$nextTick(() => {
        jQuery(this.$el).find('.ui.dropdown').dropdown({
          selectOnKeydown: false,
          action: function (text, value, $el) {
            // used ton ensure focusing the dropdown and clicking via keyboard
            // works as expected
            self.$refs[$el.data('ref')].click()
            jQuery(self.$el).find('.ui.dropdown').dropdown('hide')
          },
        })
        jQuery(this.$el).find('.ui.dropdown').dropdown('show', function () {
          // little magic to ensure the menu is always visible in the viewport
          // By default, try to diplay it on the right if there is enough room
          let menu = jQuery(self.$el).find('.ui.dropdown').find(".menu")
          let viewportOffset = menu.get(0).getBoundingClientRect();
          let left = viewportOffset.left;
          let viewportWidth = document.documentElement.clientWidth
          let rightOverflow = viewportOffset.right - viewportWidth
          let leftOverflow = -viewportOffset.left
          let offset = 0
          if (rightOverflow > 0) {
            offset = -rightOverflow - 5
            menu.css({cssText: `left: ${offset}px !important;`});
          }
          else if (leftOverflow > 0) {
            offset = leftOverflow  + 5
            menu.css({cssText: `right: -${offset}px !important;`});
          }
        })
      })
    }
  }
}
</script>
