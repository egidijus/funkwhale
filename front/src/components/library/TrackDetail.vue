<template>

  <div v-if="track">
    <section class="ui vertical stripe segment">
      <div class="ui stackable grid row container">
        <div class="six wide column">
          <img class="image" alt="" v-if="cover && cover.original" v-lazy="$store.getters['instance/absoluteUrl'](cover.square_crop)">
          <template v-if="upload">
            <h3 class="ui header">
              <translate key="1" v-if="track.artist.content_category === 'music'" translate-context="Content/*/*">Track Details</translate>
              <translate key="2" v-else translate-context="Content/*/*">Episode Details</translate>
            </h3>
            <table class="ui basic table">
              <tbody>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*">Duration</translate>
                  </td>
                  <td class="right aligned">
                    <template v-if="upload.duration">{{ upload.duration | duration }}</template>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*/Noun">Size</translate>
                  </td>
                  <td class="right aligned">
                    <template v-if="upload.size">{{ upload.size | humanSize }}</template>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*/Noun">Codec</translate>
                  </td>
                  <td class="right aligned">
                    <template v-if="upload.extension">{{ upload.extension }}</template>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/Track/*/Noun">Bitrate</translate>
                  </td>
                  <td class="right aligned">
                    <template v-if="upload.bitrate">{{ upload.bitrate | humanSize }}/s</template>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*">Downloads</translate>
                  </td>
                  <td class="right aligned">
                    {{ track.downloads_count }}
                  </td>
                </tr>
              </tbody>
            </table>

          </template>
        </div>
        <div class="ten wide column">
          <template v-if="track.tags && track.tags.length > 0">
            <tags-list :tags="track.tags"></tags-list>
            <div class="ui hidden divider"></div>
          </template>

          <rendered-description
            :content="track.description"
            :can-update="false"></rendered-description>
          <h2 class="ui header">
            <translate translate-context="Content/*/*">Release Details</translate>
          </h2>
          <table class="ui basic table ellipsis-rows">
            <tbody>
              <tr>
                <td>
                  <translate translate-context="*/*/*/Noun">Artist</translate>
                </td>
                <td class="right aligned">
                  <router-link :to="{name: 'library.artists.detail', params: {id: track.artist.id}}">
                    {{ track.artist.name }}
                  </router-link>
                </td>
              </tr>
              <tr v-if="track.album">
                <td>
                  <translate key="1" v-if="track.album.artist.content_category === 'music'" translate-context="*/*/*/Noun">Album</translate>
                  <translate key="2" v-else translate-context="*/*/*">Serie</translate>
                </td>
                <td class="right aligned">
                  <router-link :to="{name: 'library.albums.detail', params: {id: track.album.id}}">
                    {{ track.album.title }}
                  </router-link>
                </td>
              </tr>
              <tr>
                <td>
                  <translate translate-context="*/*/*">Year</translate>
                </td>
                <td class="right aligned">
                  <template v-if="track.album && track.album.release_date">
                    {{ track.album.release_date | moment('Y') }}
                  </template>
                  <template v-else>
                    <translate translate-context="*/*/*">N/A</translate>
                  </template>
                </td>
              </tr>
              <tr>
                <td>
                  <translate translate-context="Content/Track/*/Noun">Copyright</translate>
                </td>
                <td class="right aligned">
                  <span v-if="track.copyright" :title="track.copyright">{{ track.copyright|truncate(50) }}</span>
                  <template v-else>
                    <translate translate-context="*/*/*">N/A</translate>
                  </template>
                </td>
              </tr>
              <tr>
                <td>
                  <translate translate-context="Content/*/*/Noun">License</translate>
                </td>
                <td class="right aligned">
                  <a v-if="license" :href="license.url" target="_blank" rel="noopener noreferrer">{{ license.name }}</a>
                  <translate v-else translate-context="*/*/*">N/A</translate>
                </td>
              </tr>
              <tr v-if="!track.is_local">
                <td>
                  <translate translate-context="Content/*/*/Noun">URL</translate>
                </td>
                <td :title="track.fid">
                  <a :href="track.fid" target="_blank" rel="noopener noreferrer">
                    {{ track.fid|truncate(65)}}
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
          <a v-if="musicbrainzUrl" :href="musicbrainzUrl" target="_blank" rel="noreferrer noopener">
            <i class="external icon"></i>
            <translate translate-context="Content/*/*/Clickable, Verb">View on MusicBrainz</translate>
          </a>
          <h2 class="ui header">
            <translate translate-context="Content/*/Title/Noun">Related Playlists</translate>
          </h2>
          <playlist-widget :url="'playlists/'" :filters="{track: track.id, playable: true, ordering: '-modification_date'}">
          </playlist-widget>

          <h2 class="ui header">
            <translate translate-context="Content/*/Title/Noun">Related Libraries</translate>
          </h2>
          <library-widget @loaded="$emit('libraries-loaded', $event)" :url="'tracks/' + id + '/libraries/'">
            <translate translate-context="Content/Track/Paragraph" slot="subtitle">This track is present in the following libraries:</translate>
          </library-widget>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import axios from "axios"
import url from "@/utils/url"
import logger from "@/logging"
import LibraryWidget from "@/components/federation/LibraryWidget"
import TagsList from "@/components/tags/List"
import PlaylistWidget from "@/components/playlists/Widget"

const FETCH_URL = "tracks/"

export default {
  props: ["track", "libraries"],
  components: {
    LibraryWidget,
    TagsList,
    PlaylistWidget,
  },
  data() {
    return {
      id: this.track.id,
      licenseData: null
    }
  },
  created() {
    if (this.track && this.track.license) {
      this.fetchLicenseData(this.track.license)
    }
  },
  methods: {
    fetchLicenseData(licenseId) {
      var self = this
      let url = `licenses/${licenseId}`
      axios.get(url).then(response => {
        self.licenseData = response.data
      })
    },
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('*/*/*/Noun', "Track")
      }
    },
    musicbrainzUrl() {
      if (this.track.mbid) {
        return "https://musicbrainz.org/recording/" + this.track.mbid
      }
    },
    upload() {
      if (this.track.uploads) {
        return this.track.uploads[0]
      }
    },
    license() {
      if (!this.track || !this.track.license) {
        return null
      }
      return this.licenseData
    },
    cover () {
      if (this.track.cover && this.track.cover.original) {
        return this.track.cover
      }
      if (this.track.album && this.track.album.cover) {
        return this.track.album.cover
      }
    },
  },
  watch: {
    track (v) {
      if (v && v.license) {
        this.fetchLicenseData(v.license)
      }
    }
  }
}
</script>
