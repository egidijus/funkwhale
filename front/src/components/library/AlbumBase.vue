<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment" v-title="labels.title">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="object">
      <section class="ui vertical stripe segment channel-serie">
        <div class="ui stackable grid container">
          <div class="ui seven wide column">
            <div v-if="isSerie" class="padded basic segment">
              <div class="ui two column grid" v-if="isSerie">
                <div class="column">
                  <div class="large two-images">
                    <img class="channel-image" v-if="object.cover && object.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](object.cover.square_crop)">
                    <img class="channel-image" v-else src="../../assets/audio/default-cover.png">
                    <img class="channel-image" v-if="object.cover && object.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](object.cover.square_crop)">
                    <img class="channel-image" v-else src="../../assets/audio/default-cover.png">
                  </div>
                </div>
                <div class="ui column right aligned">
                  <tags-list v-if="object.tags && object.tags.length > 0" :tags="object.tags"></tags-list>
                  <div class="ui small hidden divider"></div>
                  <human-duration v-if="totalDuration > 0" :duration="totalDuration"></human-duration>
                  <template v-if="totalTracks > 0">
                    <div class="ui hidden very small divider"></div>
                    <translate key="1" v-if="isSerie" translate-context="Content/Channel/Paragraph"
                      translate-plural="%{ count } episodes"
                      :translate-n="totalTracks"
                      :translate-params="{count: totalTracks}">
                      %{ count } episode
                    </translate>
                    <translate v-else translate-context="*/*/*" :translate-params="{count: totalTracks}" :translate-n="totalTracks" translate-plural="%{ count } tracks">%{ count } track</translate>
                  </template>
                  <div class="ui small hidden divider"></div>
                  <play-button class="vibrant" :tracks="object.tracks"></play-button>
                  <div class="ui hidden horizontal divider"></div>
                  <album-dropdown
                    :object="object"
                    :public-libraries="publicLibraries"
                    :is-loading="isLoading"
                    :is-album="isAlbum"
                    :is-serie="isSerie"
                    :is-channel="isChannel"
                    :artist="artist"></album-dropdown>
                </div>
              </div>
              <div class="ui small hidden divider"></div>
              <header>
                <h2 class="ui header" :title="object.title">
                  {{ object.title }}
                </h2>
                <artist-label :artist="artist"></artist-label>
              </header>
            </div>
            <div v-else class="ui center aligned text padded basic segment">
              <img class="channel-image" v-if="object.cover && object.cover.original" v-lazy="$store.getters['instance/absoluteUrl'](object.cover.square_crop)">
              <img class="channel-image" v-else src="../../assets/audio/default-cover.png">
              <div class="ui hidden divider"></div>
              <header>
                <h2 class="ui header" :title="object.title">
                  {{ object.title }}
                </h2>
                <artist-label class="rounded" :artist="artist"></artist-label>
              </header>
              <div class="ui small hidden divider"></div>
              <template v-if="totalTracks > 0">
                <div class="ui hidden very small divider"></div>
                <translate key="1" v-if="isSerie" translate-context="Content/Channel/Paragraph"
                  translate-plural="%{ count } episodes"
                  :translate-n="totalTracks"
                  :translate-params="{count: totalTracks}">
                  %{ count } episode
                </translate>
                <translate v-else translate-context="*/*/*" :translate-params="{count: totalTracks}" :translate-n="totalTracks" translate-plural="%{ count } tracks">%{ count } track</translate> ·
              </template>
              <human-duration v-if="totalDuration > 0" :duration="totalDuration"></human-duration>
              <div class="ui small hidden divider"></div>
              <play-button class="vibrant" :tracks="object.tracks"></play-button>
              <div class="ui horizontal hidden divider"></div>
              <album-dropdown
                :object="object"
                :public-libraries="publicLibraries"
                :is-loading="isLoading"
                :is-album="isAlbum"
                :is-serie="isSerie"
                :is-channel="isChannel"
                :artist="artist"></album-dropdown>
              <div v-if="(object.tags && object.tags.length > 0) || object.description || $store.state.auth.authenticated && object.is_local">
                <div class="ui small hidden divider"></div>
                <div class="ui divider"></div>
                <div class="ui small hidden divider"></div>
                <template v-if="object.tags && object.tags.length > 0" >
                  <tags-list :tags="object.tags"></tags-list>
                  <div class="ui small hidden divider"></div>
                </template>
                <rendered-description
                  v-if="object.description"
                  :content="object.description"
                  :can-update="false"></rendered-description>
                <router-link v-else-if="$store.state.auth.authenticated && object.is_local" :to="{name: 'library.albums.edit', params: {id: object.id }}">
                  <i class="pencil icon"></i>
                  <translate translate-context="Content/*/Button.Label/Verb">Add a description…</translate>
                </router-link>
              </div>
            </div>
            <template v-if="isSerie">
              <div class="ui hidden divider"></div>
              <rendered-description
                v-if="object.description"
                :content="object.description"
                :can-update="false"></rendered-description>
              <router-link v-else-if="$store.state.auth.authenticated && object.is_local" :to="{name: 'library.albums.edit', params: {id: object.id }}">
                <i class="pencil icon"></i>
                <translate translate-context="Content/*/Button.Label/Verb">Add a description…</translate>
              </router-link>

            </template>
          </div>
          <div class="nine wide column">
            <router-view v-if="object" :paginate-by="paginateBy" :page="page" :total-tracks="totalTracks" :is-serie="isSerie" :artist="artist" :discs="discs" @libraries-loaded="libraries = $event" :object="object" object-type="album" :key="$route.fullPath" @page-changed="page = $event"></router-view>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script>
import axios from "axios"
import lodash from "@/lodash"
import backend from "@/audio/backend"
import PlayButton from "@/components/audio/PlayButton"
import TagsList from "@/components/tags/List"
import ArtistLabel from '@/components/audio/ArtistLabel'
import AlbumDropdown from './AlbumDropdown'

function groupByDisc(acc, track) {
  var dn = track.disc_number - 1
  if (dn < 0) dn = 0
  if (acc[dn] == undefined) {
    acc.push([track])
  } else {
    acc[dn].push(track)
  }
  return acc
}

export default {
  props: ["id"],
  components: {
    PlayButton,
    TagsList,
    ArtistLabel,
    AlbumDropdown
  },
  data() {
    return {
      isLoading: true,
      object: null,
      artist: null,
      discs: [],
      libraries: [],
      page: 1,
      paginateBy: 50,
    }
  },
  async created() {
    await this.fetchData()
  },
  methods: {
    async fetchData() {
      this.isLoading = true
      let tracksResponse = axios.get(`tracks/`, {params: {ordering: 'disc_number,position', album: this.id, page_size: this.paginateBy, page:this.page, include_channels: 'true'}})
      let albumResponse = await axios.get(`albums/${this.id}/`, {params: {refresh: 'true'}})
      let artistResponse = await axios.get(`artists/${albumResponse.data.artist.id}/`)
      this.artist = artistResponse.data
      if (this.artist.channel) {
        this.artist.channel.artist = this.artist
      }
      tracksResponse = await tracksResponse
      this.object = albumResponse.data
      this.object.tracks = tracksResponse.data.results
      this.discs = this.object.tracks.reduce(groupByDisc, [])
      this.isLoading = false
    },
    remove () {
      let self = this
      self.isLoading = true
      axios.delete(`albums/${this.object.id}`).then((response) => {
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
    totalTracks () {
      return this.object.tracks_count
    },
    isChannel () {
      return this.object.artist.channel
    },
    isSerie () {
      return this.object.artist.content_category === 'podcast'
    },
    isAlbum () {
      return this.object.artist.content_category === 'music'
    },
    totalDuration () {
      let durations = [0]
      this.object.tracks.forEach((t) => {
        if (t.uploads[0] && t.uploads[0].duration) {
          durations.push(t.uploads[0].duration)
        }
      })
      return lodash.sum(durations)
    },
    labels() {
      return {
        title: this.$pgettext('*/*/*', 'Album'),
      }
    },
    publicLibraries () {
      return this.libraries.filter(l => {
        return l.privacy_level === 'everyone'
      })
    },
  },
  watch: {
    id() {
      this.fetchData()
    },
    page() {
      this.fetchData()
    }
  }
}
</script>
