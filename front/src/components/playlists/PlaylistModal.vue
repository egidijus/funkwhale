<template>
  <modal @update:show="update" :show="$store.state.playlists.showModal">
    <div class="header">
      <template v-if="track">
        <h2 class="ui header">
          <translate translate-context="Popup/Playlist/Title/Verb">Add to playlist</translate>
          <div
            class="ui sub header"
            translate-context="Popup/Playlist/Paragraph"
            v-translate="{artist: track.artist.name, title: track.title}"
            :translate-params="{artist: track.artist.name, title: track.title}">
            "%{ title }", by %{ artist }
          </div>
        </h2>
      </template>
      <translate v-else translate-context="Popup/Playlist/Title/Verb">Manage playlists</translate>
    </div>
    <div class="scrolling content">
      <playlist-form :key="formKey"></playlist-form>
      <div class="ui divider"></div>
      <div v-if="playlists.length > 0">
        <div v-if="showDuplicateTrackAddConfirmation" role="alert" class="ui warning message">
          <p translate-context="Popup/Playlist/Paragraph"
            v-translate="{track: track.title, playlist: duplicateTrackAddInfo.playlist_name}"
            :translate-params="{track: track.title, playlist: duplicateTrackAddInfo.playlist_name}"><strong>%{ track }</strong> is already in <strong>%{ playlist }</strong>.</p>
          <button
            @click="duplicateTrackAddConfirm(false)"
            class="ui small basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
          </button>
          <button
            class="ui small green button"
            @click="addToPlaylist(lastSelectedPlaylist, true)">
              <translate translate-context="*/Playlist/Button.Label/Verb">Add anyways</translate></button>
        </div>
        <div v-if="errors.length > 0" role="alert" class="ui negative message">
          <div class="header"><translate translate-context="Popup/Playlist/Error message.Title">The track can't be added to a playlist</translate></div>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
        <h4 class="ui header"><translate translate-context="Popup/Playlist/Title">Available playlists</translate></h4>
        <div class="ui form">
          <div class="fields">
            <div class="field">
              <label for="playlist-name-filter"><translate translate-context="Popup/Playlist/Label">Filter</translate></label>
              <input name="playlist-name-filter" v-model="playlistNameFilter" type="text" class="inline" :placeholder="labels.filterPlaylistField" />
            </div>
          </div>
        </div>
        <table v-if="sortedPlaylists.length > 0" class="ui unstackable very basic table">
          <thead>
            <tr>
              <th></th>
              <th><translate translate-context="*/*/*/Noun">Name</translate></th>
              <th class="sorted descending"><translate translate-context="Popup/Playlist/Table.Label/Short">Last modification</translate></th>
              <th><translate translate-context="*/*/*">Tracks</translate></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="playlist in sortedPlaylists">
              <td>
                <router-link
                  class="ui icon basic small button"
                  :to="{name: 'library.playlists.detail', params: {id: playlist.id }, query: {mode: 'edit'}}"><i class="ui pencil icon"></i></router-link>
              </td>
              <td :title="playlist.name">
                <router-link v-on:click.native="update(false)" :to="{name: 'library.playlists.detail', params: {id: playlist.id }}">{{ playlist.name }}</router-link></td>
              <td><human-date :date="playlist.modification_date"></human-date></td>
              <td>{{ playlist.tracks_count }}</td>
              <td>
                <div
                  v-if="track"
                  class="ui green icon basic small right floated button"
                  :title="labels.addToPlaylist"
                  @click="addToPlaylist(playlist.id, false)">
                  <i class="plus icon"></i> <translate translate-context="Popup/Playlist/Table.Button.Label/Verb">Add track</translate>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <template v-else>
          <div class="ui small placeholder segment">
            <div class="ui header">
               <translate translate-context="Popup/Playlist/EmptyState">No results matching your filter</translate>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="ui placeholder segment">
            <div class="ui icon header">
              <i class="list icon"></i>
              <translate translate-context="Content/Home/Placeholder">
                No playlists have been created yet
              </translate>
            </div>
          </div>
        </template>
      </div>
    </div>
    <div class="actions">
      <div class="ui basic cancel button"><translate translate-context="*/*/Button.Label/Verb">Cancel</translate></div>
    </div>
  </modal>
</template>

<script>
import filter from "lodash/fp/filter";
import sortBy from "lodash/fp/sortBy";
import flow from "lodash/fp/flow";

import axios from 'axios'
import {mapState} from 'vuex'

import logger from '@/logging'
import Modal from '@/components/semantic/Modal'
import PlaylistForm from '@/components/playlists/Form'

export default {
  components: {
    Modal,
    PlaylistForm
  },
  data () {
    return {
      formKey: String(new Date()),
      errors: [],
      playlistNameFilter: '',
      duplicateTrackAddInfo: {},
      showDuplicateTrackAddConfirmation: false,
      lastSelectedPlaylist: -1,
    }
  },
  methods: {
    update (v) {
      this.$store.commit('playlists/showModal', v)
    },
    addToPlaylist (playlistId, allowDuplicate) {
      let self = this
      let payload = {
        track: this.track.id,
        playlist: playlistId,
        allow_duplicates: allowDuplicate
      }

      self.lastSelectedPlaylist = playlistId

      return axios.post('playlist-tracks/', payload).then(response => {
        logger.default.info('Successfully added track to playlist')
        self.update(false)
        self.$store.dispatch('playlists/fetchOwn')
      }, error => {
        if (error.backendErrors.length == 1 && error.backendErrors[0].code == 'tracks_already_exist_in_playlist') {
          self.duplicateTrackAddInfo = error.backendErrors[0]
          self.showDuplicateTrackAddConfirmation = true
        } else {
          self.errors = error.backendErrors
          self.showDuplicateTrackAddConfirmation = false
        }
      })
    },
    duplicateTrackAddConfirm (v) {
      this.showDuplicateTrackAddConfirmation = v
    }
  },
  computed: {
    ...mapState({
      playlists: state => state.playlists.playlists,
      track: state => state.playlists.modalTrack
    }),
    labels () {
      return {
        addToPlaylist: this.$pgettext('Popup/Playlist/Table.Button.Tooltip/Verb', 'Add to this playlist'),
        filterPlaylistField: this.$pgettext('Popup/Playlist/Form/Placeholder', 'Enter playlist name')
      }
    },
    sortedPlaylists () {
      let regexp = new RegExp(this.playlistNameFilter, 'i');
      let p = flow(
        filter((e) => e.name.match(regexp) !== null),
        sortBy((e) => { return e.modification_date }),
      )(this.playlists)
      p.reverse()
      return p
    }
  },
  watch: {
    '$store.state.route.path' () {
      this.$store.commit('playlists/showModal', false)
      this.showDuplicateTrackAddConfirmation = false
    },
    '$store.state.playlists.showModal' () {
      this.formKey = String(new Date())
      this.showDuplicateTrackAddConfirmation = false
    }
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
.ui.small.placeholder.segment {
  min-height: auto;
}
</style>
