<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment" v-title="labels.playlist">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <section v-if="!isLoading && playlist" class="ui head vertical center aligned stripe segment" v-title="playlist.name">
      <div class="segment-content">
        <h2 class="ui center aligned icon header">
          <i class="circular inverted list warning icon"></i>
          <div class="content">
            {{ playlist.name }}
            <div class="sub header">
              <translate
                translate-plural="Playlist containing %{ count } tracks, by %{ username }"
                :translate-n="playlist.tracks_count"
                :translate-params="{count: playlist.tracks_count, username: playlist.user.username}"
                translate-context="Content/Playlist/Header.Subtitle">
                Playlist containing %{ count } track, by %{ username }
              </translate><br>
              <duration :seconds="playlist.duration" />
            </div>
          </div>
        </h2>
        <div class="ui hidden divider"></div>
        <play-button class="vibrant" :is-playable="playlist.is_playable" :tracks="tracks"><translate translate-context="Content/Queue/Button.Label/Short, Verb">Play all</translate></play-button>
        <button
          class="ui icon labeled button"
          v-if="$store.state.auth.profile && playlist.user.id === $store.state.auth.profile.id"
          @click="edit = !edit">
          <i class="pencil icon"></i>
          <template v-if="edit"><translate translate-context="Content/Playlist/Button.Label/Verb">Stop Editing</translate></template>
          <template v-else><translate translate-context="Content/*/Button.Label/Verb">Edit</translate></template>
        </button>
        <button
          class="ui icon labeled button"
          v-if="playlist.privacy_level === 'everyone' && playlist.is_playable"
          @click="showEmbedModal = !showEmbedModal">
          <i class="code icon"></i>
          <translate translate-context="Content/*/Button.Label/Verb">Embed</translate>
        </button>

        <dangerous-button v-if="$store.state.auth.profile && playlist.user.id === $store.state.auth.profile.id" class="ui labeled danger icon button" :action="deletePlaylist">
          <i class="trash icon"></i> <translate translate-context="*/*/*/Verb">Delete</translate>
          <p slot="modal-header" v-translate="{playlist: playlist.name}" translate-context="Popup/Playlist/Title/Call to action" :translate-params="{playlist: playlist.name}">
            Do you want to delete the playlist "%{ playlist }"?
          </p>
          <p slot="modal-content"><translate translate-context="Popup/Playlist/Paragraph">This will completely delete this playlist and cannot be undone.</translate></p>
          <div slot="modal-confirm"><translate translate-context="Popup/Playlist/Button.Label/Verb">Delete playlist</translate></div>
        </dangerous-button>
      </div>
      <modal v-if="playlist.privacy_level === 'everyone' && playlist.is_playable" :show.sync="showEmbedModal">
        <h4 class="header">
          <translate translate-context="Popup/Album/Title/Verb">Embed this playlist on your website</translate>
        </h4>
        <div class="scrolling content">
          <div class="description">
            <embed-wizard type="playlist" :id="playlist.id" />
          </div>
        </div>
        <div class="actions">
          <div class="ui basic deny button">
            <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
          </div>
        </div>
      </modal>
    </section>
    <section class="ui vertical stripe segment">
      <template v-if="edit">
        <playlist-editor
          @playlist-updated="playlist = $event"
          @tracks-updated="updatePlts"
          :playlist="playlist" :playlist-tracks="playlistTracks"></playlist-editor>
      </template>
      <template v-else-if="tracks.length > 0">
        <h2><translate translate-context="*/*/*">Tracks</translate></h2>
        <track-table :display-position="true" :tracks="tracks"></track-table>
      </template>
      <div v-else class="ui placeholder segment">
        <div class="ui icon header">
          <i class="list icon"></i>
          <translate translate-context="Content/Home/Placeholder">There are no tracks in this playlist yet</translate>
        </div>
        <button @click="edit = !edit" class="ui success icon labeled button">
          <i class="pencil icon"></i>
          <translate translate-context="Content/Home/CreatePlaylist">Edit</translate>
        </button>
      </div>
    </section>
  </main>
</template>
<script>
import axios from "axios"
import TrackTable from "@/components/audio/track/Table"
import RadioButton from "@/components/radios/Button"
import PlayButton from "@/components/audio/PlayButton"
import PlaylistEditor from "@/components/playlists/Editor"
import EmbedWizard from "@/components/audio/EmbedWizard"
import Modal from '@/components/semantic/Modal'

export default {
  props: {
    id: { required: true },
    defaultEdit: { type: Boolean, default: false }
  },
  components: {
    PlaylistEditor,
    TrackTable,
    PlayButton,
    RadioButton,
    Modal,
    EmbedWizard,
  },
  data: function() {
    return {
      edit: this.defaultEdit,
      isLoading: false,
      playlist: null,
      tracks: [],
      playlistTracks: [],
      showEmbedModal: false,
    }
  },
  created: function() {
    this.fetch()
  },
  computed: {
    labels() {
      return {
        playlist: this.$pgettext('*/*/*', 'Playlist')
      }
    }
  },
  methods: {
    updatePlts(v) {
      this.playlistTracks = v
      this.tracks = v.map((e, i) => {
        let track = e.track
        track.position = i + 1
        return track
      })
    },
    fetch: function() {
      let self = this
      self.isLoading = true
      let url = "playlists/" + this.id + "/"
      axios.get(url).then(response => {
        self.playlist = response.data
        axios
          .get(url + "tracks/")
          .then(response => {
            self.updatePlts(response.data.results)
          })
          .then(() => {
            self.isLoading = false
          })
      })
    },
    deletePlaylist() {
      let self = this
      let url = "playlists/" + this.id + "/"
      axios.delete(url).then(response => {
        self.$store.dispatch("playlists/fetchOwn")
        self.$router.push({
          path: "/library"
        })
      })
    }
  }
}
</script>
