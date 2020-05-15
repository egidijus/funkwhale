<template>
  <div>
    <h2><translate translate-context="Content/Search/Title">Search for some music</translate></h2>
    <div :class="['ui', {'loading': isLoading }, 'search']">
      <div class="ui icon big input">
        <i class="search icon"></i>
        <input ref="search" class="prompt" :placeholder="labels.searchPlaceholder" v-model.trim="query" type="text" />
      </div>
    </div>
    <template v-if="query.length > 0">
      <h3 class="ui title"><translate translate-context="*/*/*/Noun">Artists</translate></h3>
      <div v-if="results.artists.length > 0">
        <div class="ui cards">
          <artist-card :key="artist.id" v-for="artist in results.artists" :artist="artist" ></artist-card>
        </div>
      </div>
      <p v-else><translate translate-context="Content/Search/Paragraph">No artist matched your query</translate></p>
    </template>
    <template v-if="query.length > 0">
      <h3 class="ui title"><translate translate-context="*/*/*">Albums</translate></h3>
      <div v-if="results.albums.length > 0" class="ui stackable three column grid">
        <div class="column" :key="album.id" v-for="album in results.albums">
          <album-card class="fluid" :album="album" ></album-card>
        </div>
      </div>
      <p v-else><translate translate-context="Content/Search/Paragraph">No album matched your query</translate></p>
    </template>
  </div>
</template>

<script>
import _ from '@/lodash'
import axios from 'axios'
import logger from '@/logging'
import AlbumCard from '@/components/audio/album/Card'
import ArtistCard from '@/components/audio/artist/Card'

export default {
  components: {
    AlbumCard,
    ArtistCard
  },
  props: {
    autofocus: {type: Boolean, default: false}
  },
  data () {
    return {
      query: '',
      results: {
        albums: [],
        artists: []
      },
      isLoading: false
    }
  },
  mounted () {
    if (this.autofocus) {
      this.$refs.search.focus()
    }
    this.search()
  },
  computed: {
    labels () {
      return {
        searchPlaceholder: this.$pgettext('*/Search/Input.Placeholder', 'Artist, album, track…')
      }
    }
  },
  methods: {
    search: _.debounce(function () {
      if (this.query.length < 1) {
        return
      }
      var self = this
      self.isLoading = true
      logger.default.debug('Searching track matching "' + this.query + '"')
      let params = {
        query: this.query
      }
      axios.get('search', {
        params: params
      }).then((response) => {
        self.results = self.castResults(response.data)
        self.isLoading = false
      })
    }, 500),
    castResults (results) {
      return {
        albums: results.albums,
        artists: results.artists
      }
    }
  },
  watch: {
    query () {
      this.search()
    }
  }
}
</script>
