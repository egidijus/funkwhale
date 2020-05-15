<template>
  <main v-title="labels.title" :key="$router.currentRoute.name">
    <section class="ui vertical stripe segment">
      <div class="ui stackable three column grid">
        <div class="column">
          <track-widget :url="'history/listenings/'" :filters="{scope: scope, ordering: '-creation_date'}">
            <template slot="title"><translate translate-context="Content/Home/Title">Recently listened</translate></template>
          </track-widget>
        </div>
        <div class="column">
          <track-widget :url="'favorites/tracks/'" :filters="{scope: scope, ordering: '-creation_date'}">
            <template slot="title"><translate translate-context="Content/Home/Title">Recently favorited</translate></template>
          </track-widget>
        </div>
        <div class="column">
          <playlist-widget :url="'playlists/'" :filters="{scope: scope, playable: true, ordering: '-modification_date'}">
            <template slot="title"><translate translate-context="*/*/*">Playlists</translate></template>
          </playlist-widget>
        </div>
      </div>
      <div class="ui section hidden divider"></div>
      <div class="ui stackable one column grid">
        <div class="column">
          <album-widget :filters="{scope: scope, playable: true, ordering: '-creation_date'}">
            <template slot="title"><translate translate-context="Content/Home/Title">Recently added</translate></template>
          </album-widget>
        </div>
      </div>
      <template v-if="scope === 'all'">
        <h3 class="ui header" >
          <translate translate-context="*/*/*">New channels</translate>
        </h3>
        <channels-widget :show-modification-date="true" :limit="12" :filters="{ordering: '-creation_date', external: 'false'}"></channels-widget>
      </template>


    </section>
  </main>
</template>

<script>
import axios from "axios"
import Search from "@/components/audio/Search"
import logger from "@/logging"
import ChannelsWidget from "@/components/audio/ChannelsWidget"
import ArtistCard from "@/components/audio/artist/Card"
import TrackWidget from "@/components/audio/track/Widget"
import AlbumWidget from "@/components/audio/album/Widget"
import PlaylistWidget from "@/components/playlists/Widget"

const ARTISTS_URL = "artists/"

export default {
  name: "library",
  props: {
    scope: {default: 'all'}
  },
  components: {
    Search,
    ArtistCard,
    TrackWidget,
    AlbumWidget,
    PlaylistWidget,
    ChannelsWidget,
  },
  data() {
    return {
      artists: [],
      isLoadingArtists: false,
    }
  },
  created() {
    this.fetchArtists()
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/Home/Title', "Home")
      }
    }
  },
  methods: {
    fetchArtists() {
      var self = this
      this.isLoadingArtists = true
      let params = {
        ordering: "-creation_date",
        playable: true
      }
      let url = ARTISTS_URL
      logger.default.time("Loading latest artists")
      axios.get(url, { params: params }).then(response => {
        self.artists = response.data.results
        logger.default.timeEnd("Loading latest artists")
        self.isLoadingArtists = false
      })
    }
  }
}
</script>
