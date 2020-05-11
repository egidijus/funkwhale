<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment" v-title="labels.title">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="track">
      <section
        :class="['ui', 'head', 'vertical', 'center', 'aligned', 'stripe', 'segment']"
        v-title="track.title"
      >
        <div class="ui basic padded segment">
          <div class="ui stackable grid row container">
            <div class="eight wide left aligned column">
              <h1 class="ui header">
                {{ track.title }}
                <div class="sub header" v-html="subtitle"></div>
              </h1>
            </div>
            <div class="eight wide right aligned column button-group">
              <play-button class="orange" :track="track">
                <translate translate-context="*/Queue/Button.Label/Short, Verb">Play</translate>
              </play-button>
              &nbsp;
              <track-favorite-icon v-if="$store.state.auth.authenticated" :border="true" :track="track"></track-favorite-icon>
              <track-playlist-icon class="circular" v-if="$store.state.auth.authenticated" :border="true" :track="track"></track-playlist-icon>
              <a v-if="upload" :href="downloadUrl" target="_blank" class="ui basic circular icon button" :title="labels.download">
                <i class="download icon"></i>
              </a>
              <modal v-if="publicLibraries.length > 0" :show.sync="showEmbedModal">
                <div class="header">
                  <translate translate-context="Popup/Track/Title">Embed this track on your website</translate>
                </div>
                <div class="content">
                  <div class="description">
                    <embed-wizard type="track" :id="track.id" />
                  </div>
                </div>
                <div class="actions">
                  <div class="ui basic deny button">
                    <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
                  </div>
                </div>
              </modal>
              <div class="ui floating dropdown circular icon basic button" :title="labels.more" v-dropdown="{direction: 'downward'}">
                <i class="ellipsis vertical icon"></i>
                <div class="menu" style="right: 0; left: auto">
                  <div
                    role="button"
                    v-if="publicLibraries.length > 0"
                    @click="showEmbedModal = !showEmbedModal"
                    class="basic item">
                    <i class="code icon"></i>
                    <translate translate-context="Content/*/Button.Label/Verb">Embed</translate>
                  </div>
                  <a :href="wikipediaUrl" target="_blank" rel="noreferrer noopener" class="basic item">
                    <i class="wikipedia w icon"></i>
                    <translate translate-context="Content/*/Button.Label/Verb">Search on Wikipedia</translate>
                  </a>
                  <a v-if="discogsUrl" :href="discogsUrl" target="_blank" rel="noreferrer noopener" class="basic item">
                    <i class="external icon"></i>
                    <translate translate-context="Content/*/Button.Label/Verb">Search on Discogs</translate>
                  </a>
                  <router-link
                    v-if="track.is_local"
                    :to="{name: 'library.tracks.edit', params: {id: track.id }}"
                    class="basic item">
                    <i class="edit icon"></i>
                    <translate translate-context="Content/*/Button.Label/Verb">Edit</translate>
                  </router-link>
                  <dangerous-button
                    :class="['ui', {loading: isLoading}, 'item']"
                    v-if="artist && $store.state.auth.authenticated && artist.channel && artist.attributed_to.full_username === $store.state.auth.fullUsername"
                    @confirm="remove()">
                    <i class="ui trash icon"></i>
                    <translate translate-context="*/*/*/Verb">Delete…</translate>
                    <p slot="modal-header"><translate translate-context="Popup/Channel/Title">Delete this track?</translate></p>
                    <div slot="modal-content">
                      <p><translate translate-context="Content/Moderation/Paragraph">The track will be deleted, as well as any related files and data. This action is irreversible.</translate></p>
                    </div>
                    <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
                  </dangerous-button>
                  <div class="divider"></div>
                  <div
                    role="button"
                    class="basic item"
                    v-for="obj in getReportableObjs({track})"
                    :key="obj.target.type + obj.target.id"
                    @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
                    <i class="share icon" /> {{ obj.label }}
                  </div>
                  <div class="divider"></div>
                  <router-link class="basic item" v-if="$store.state.auth.availablePermissions['library']" :to="{name: 'manage.library.tracks.detail', params: {id: track.id}}">
                    <i class="wrench icon"></i>
                    <translate translate-context="Content/Moderation/Link">Open in moderation interface</translate>
                  </router-link>
                  <a
                    v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
                    class="basic item"
                    :href="$store.getters['instance/absoluteUrl'](`/api/admin/music/track/${track.id}`)"
                    target="_blank" rel="noopener noreferrer">
                    <i class="wrench icon"></i>
                    <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <router-view v-if="track" @libraries-loaded="libraries = $event" :track="track" :object="track" object-type="track" :key="$route.fullPath"></router-view>
    </template>
  </main>
</template>

<script>
import time from "@/utils/time"
import axios from "axios"
import url from "@/utils/url"
import logger from "@/logging"
import PlayButton from "@/components/audio/PlayButton"
import TrackFavoriteIcon from "@/components/favorites/TrackFavoriteIcon"
import TrackPlaylistIcon from "@/components/playlists/TrackPlaylistIcon"
import Modal from '@/components/semantic/Modal'
import EmbedWizard from "@/components/audio/EmbedWizard"
import ReportMixin from '@/components/mixins/Report'
import {momentFormat} from '@/filters'

const FETCH_URL = "tracks/"



function escapeHtml(unsafe) {
  return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


export default {
  props: ["id"],
  mixins: [ReportMixin],
  components: {
    PlayButton,
    TrackPlaylistIcon,
    TrackFavoriteIcon,
    Modal,
    EmbedWizard,
  },
  data() {
    return {
      time,
      isLoading: true,
      track: null,
      artist: null,
      showEmbedModal: false,
      libraries: []
    }
  },
  created() {
    this.fetchData()
  },
  methods: {
    fetchData() {
      var self = this
      this.isLoading = true
      let url = FETCH_URL + this.id + "/"
      logger.default.debug('Fetching track "' + this.id + '"')
      axios.get(url, {params: {refresh: 'true'}}).then(response => {
        self.track = response.data
        axios.get(`artists/${response.data.artist.id}/`).then(response => {
          self.artist = response.data
        })
        self.isLoading = false
      })
    },
    remove () {
      let self = this
      self.isLoading = true
      axios.delete(`tracks/${this.track.id}`).then((response) => {
        self.isLoading = false
        self.$emit('deleted')
        self.$router.push({name: 'library.artists.detail', params: {id: this.artist.id}})
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  },
  computed: {
    publicLibraries () {
      return this.libraries.filter(l => {
        return l.privacy_level === 'everyone'
      })
    },
    upload() {
      if (this.track.uploads) {
        return this.track.uploads[0]
      }
    },
    labels() {
      return {
        title: this.$pgettext('*/*/*/Noun', "Track"),
        download: this.$pgettext('Content/Track/Link/Verb', "Download"),
        more: this.$pgettext('*/*/Button.Label/Noun', "More…"),
      }
    },
    wikipediaUrl() {
      return (
        "https://en.wikipedia.org/w/index.php?search=" +
        encodeURI(this.track.title + " " + this.track.artist.name)
      )
    },
    discogsUrl() {
      if (this.track.album) {
        return (
          "https://discogs.com/search/?type=release&title=" +
    encodeURI(this.track.album.title) + "&artist=" +
    encodeURI(this.track.artist.name) + "&track=" +
    encodeURI(this.track.title)
        )

      }
    },
    downloadUrl() {
      let u = this.$store.getters["instance/absoluteUrl"](
        this.upload.listen_url
      )
      if (this.$store.state.auth.authenticated) {
        let param = "jwt"
        let value = this.$store.state.auth.token
        if (this.$store.state.auth.scopedTokens && this.$store.state.auth.scopedTokens.listen) {
          // used scoped tokens instead of JWT to reduce the attack surface if the token
          // is leaked
          param = "token"
          value = this.$store.state.auth.scopedTokens.listen
        }
        u = url.updateQueryString(
          u,
          param,
          encodeURI(value)
        )
      }
      return u
    },
    attributedToUrl () {
      let route = this.$router.resolve({
        name: 'profile.full.overview',
        params: {
          username: this.track.attributed_to.preferred_username,
          domain: this.track.attributed_to.domain
        }
      })
      return route.href
    },
    albumUrl () {
      let route = this.$router.resolve({name: 'library.albums.detail', params: {id: this.track.album.id }})
      return route.href
    },
    artistUrl () {
      let route = this.$router.resolve({name: 'library.artists.detail', params: {id: this.track.artist.id }})
      return route.href
    },
    headerStyle() {
      if (!this.cover || !this.cover.original) {
        return ""
      }
      return (
        "background-image: url(" +
        this.$store.getters["instance/absoluteUrl"](this.cover.original) +
        ")"
      )
    },
    subtitle () {
      let msg
      if (this.track.attributed_to) {
        msg = this.$pgettext('Content/Track/Paragraph', 'Uploaded by <a class="internal" href="%{ uploaderUrl }">%{ uploader }</a> on <time title="%{ date }" datetime="%{ date }">%{ prettyDate }</time>')
        return this.$gettextInterpolate(msg, {
          uploaderUrl: this.attributedToUrl,
          uploader: escapeHtml(`@${this.track.attributed_to.full_username}`),
          date: escapeHtml(this.track.creation_date),
          prettyDate: escapeHtml(momentFormat(this.track.creation_date, 'LL')),
        })
      } else {
        msg = this.$pgettext('Content/Track/Paragraph', 'Uploaded on <time title="%{ date }" datetime="%{ date }">%{ prettyDate }</time>')
        return this.$gettextInterpolate(msg, {
          date: escapeHtml(this.track.creation_date),
          prettyDate: escapeHtml(momentFormat(this.track.creation_date, 'LL')),
        })
      }
    }
  },
  watch: {
    id() {
      this.fetchData()
    },
  }
}
</script>
