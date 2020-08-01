<template>
  <div class="ui text container component-playlist-editor">
    <playlist-form @updated="$emit('playlist-updated', $event)" :title="false" :playlist="playlist"></playlist-form>
    <h3 class="ui top attached header">
      <translate translate-context="Content/Playlist/Title">Playlist editor</translate>
    </h3>
    <div class="ui attached segment">
      <template v-if="status === 'loading'">
        <div class="ui active tiny inline loader"></div>
        <translate translate-context="Content/Playlist/Paragraph">Syncing changes to server…</translate>
      </template>
      <template v-else-if="status === 'errored'">
        <i class="dangerclose icon"></i>
        <translate translate-context="Content/Playlist/Error message.Title">An error occurred while saving your changes</translate>
        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
      </template>
      <div v-else-if="status === 'confirmDuplicateAdd'" role="alert" class="ui warning message">
        <p translate-context="Content/Playlist/Paragraph"
            v-translate="{playlist: playlist.name}">Some tracks in your queue are already in this playlist:</p>
        <ul class="ui relaxed divided list duplicate-tracks-list">
          <li v-for="track in duplicateTrackAddInfo.tracks" class="ui item">{{ track }}</li>
        </ul>
        <button
          class="ui small success button"
          @click="insertMany(queueTracks, true)"><translate translate-context="*/Playlist/Button.Label/Verb">Add anyways</translate></button>
      </div>
      <template v-else-if="status === 'saved'">
        <i class="success check icon"></i> <translate translate-context="Content/Playlist/Paragraph">Changes synced with server</translate>
      </template>
    </div>
    <div class="ui bottom attached segment">
      <div
        @click="insertMany(queueTracks, false)"
        :disabled="queueTracks.length === 0"
        :class="['ui', {disabled: queueTracks.length === 0}, 'labeled', 'icon', 'button']"
        :title="labels.copyTitle">
          <i class="plus icon"></i>
          <translate translate-context="Content/Playlist/Button.Label/Verb"
            translate-plural="Insert from queue (%{ count } tracks)"
            :translate-n="queueTracks.length"
            :translate-params="{count: queueTracks.length}">
            Insert from queue (%{ count } track)
          </translate>
        </div>

      <dangerous-button :disabled="plts.length === 0" class="ui labeled right floated danger icon button" :action="clearPlaylist">
        <i class="eraser icon"></i> <translate translate-context="*/Playlist/Button.Label/Verb">Clear playlist</translate>
        <p slot="modal-header" v-translate="{playlist: playlist.name}" translate-context="Popup/Playlist/Title"  :translate-params="{playlist: playlist.name}">
          Do you want to clear the playlist "%{ playlist }"?
        </p>
        <p slot="modal-content"><translate translate-context="Popup/Playlist/Paragraph">This will remove all tracks from this playlist and cannot be undone.</translate></p>
        <div slot="modal-confirm"><translate translate-context="*/Playlist/Button.Label/Verb">Clear playlist</translate></div>
      </dangerous-button>
      <div class="ui hidden divider"></div>
      <template v-if="plts.length > 0">
        <p><translate translate-context="Content/Playlist/Paragraph/Call to action">Drag and drop rows to reorder tracks in the playlist</translate></p>
        <div class="table-wrapper">
          <table class="ui compact very basic unstackable table">
            <draggable v-model="plts" tag="tbody" @update="reorder">
              <tr v-for="(plt, index) in plts" :key="`${index}-${plt.track.id}`">
                <td class="left aligned">{{ plt.index + 1}}</td>
                <td class="center aligned">
                  <img alt="" class="ui mini image" v-if="plt.track.album && plt.track.album.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](plt.track.album.cover.small_square_crop)">
                  <img alt="" class="ui mini image" v-else src="../../assets/audio/default-cover.png">
                </td>
                <td colspan="4">
                  <strong>{{ plt.track.title }}</strong><br />
                    {{ plt.track.artist.name }}
                </td>
                <td class="right aligned">
                  <i @click.stop="removePlt(index)" class="circular danger trash icon"></i>
                </td>
              </tr>
            </draggable>
          </table>

        </div>
      </template>
    </div>
  </div>
</template>

<script>
import {mapState} from 'vuex'
import axios from 'axios'
import PlaylistForm from '@/components/playlists/Form'

import draggable from 'vuedraggable'

export default {
  components: {
    draggable,
    PlaylistForm
  },
  props: ['playlist', 'playlistTracks'],
  data () {
    return {
      plts: this.playlistTracks,
      isLoading: false,
      errors: [],
      duplicateTrackAddInfo: {},
      showDuplicateTrackAddConfirmation: false
    }
  },
  methods: {
    success () {
      this.isLoading = false
      this.errors = []
      this.showDuplicateTrackAddConfirmation = false
    },
    errored (errors) {
      this.isLoading = false
      if (errors.length == 1 && errors[0].code == 'tracks_already_exist_in_playlist') {
        this.duplicateTrackAddInfo = errors[0]
        this.showDuplicateTrackAddConfirmation = true
      } else {
        this.errors = errors
      }
    },
    reorder ({oldIndex, newIndex}) {
      let self = this
      self.isLoading = true
      let plt = this.plts[newIndex]
      let url = `playlists/${this.playlist.id}/move`
      axios.post(url, {from: oldIndex, to: newIndex}).then((response) => {
        self.success()
      }, error => {
        self.errored(error.backendErrors)
      })
    },
    removePlt (index) {
      this.plts.splice(index, 1)
      let self = this
      self.isLoading = true
      let url = `playlists/${this.playlist.id}/remove`
      axios.post(url, {index}).then((response) => {
        self.success()
        self.$store.dispatch('playlists/fetchOwn')
      }, error => {
        self.errored(error.backendErrors)
      })
    },
    clearPlaylist () {
      this.plts = []
      let self = this
      self.isLoading = true
      let url = 'playlists/' + this.playlist.id + '/clear'
      axios.delete(url).then((response) => {
        self.success()
        self.$store.dispatch('playlists/fetchOwn')
      }, error => {
        self.errored(error.backendErrors)
      })
    },
    insertMany (tracks, allowDuplicates) {
      let self = this
      let ids = tracks.map(t => {
        return t.id
      })
      let payload = {
        tracks: ids,
        allow_duplicates: allowDuplicates
      }
      self.isLoading = true
      let url = 'playlists/' + this.playlist.id + '/add/'
      axios.post(url, payload).then((response) => {
        response.data.results.forEach(r => {
          self.plts.push(r)
        })
        self.success()
        self.$store.dispatch('playlists/fetchOwn')
      }, error => {
        // if backendErrors isn't populated (e.g. duplicate track exceptions raised by
        // the playlist model), read directly from the response
        if (error.rawPayload.playlist) {
          self.errored(error.rawPayload.playlist.non_field_errors)
        } else {
          self.errored(error.backendErrors)
        }
      })
    }
  },
  computed: {
    ...mapState({
      queueTracks: state => state.queue.tracks
    }),
    labels () {
      return {
        copyTitle: this.$pgettext('Content/Playlist/Button.Tooltip/Verb', 'Copy queued tracks to playlist')
      }
    },
    status () {
      if (this.isLoading) {
        return 'loading'
      }
      if (this.errors.length > 0) {
        return 'errored'
      }
      if (this.showDuplicateTrackAddConfirmation) {
        return 'confirmDuplicateAdd'
      }
      return 'saved'
    }
  },
  watch: {
    plts: {
      handler (newValue) {
        newValue.forEach((e, i) => {
          e.index = i
        })
        this.$emit('tracks-updated', newValue)
      },
      deep: true
    }
  }
}
</script>
