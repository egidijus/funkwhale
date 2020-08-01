<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div class="ui small text container" v-if="initialId">
        <h2>{{ labels.title }}</h2>
        <remote-search-form :initial-id="initialId" :type="initialType"></remote-search-form>
      </div>
      <div class="ui container" v-else>
        <h2>
          <label for="query">
            <translate translate-context="Content/Search/Input.Label/Noun">Search</translate>
          </label>
        </h2>
        <form class="ui form" @submit.prevent="page = 1; search()">
          <div class="ui field">
            <div class="ui action input">
              <input class="ui input" id="query" name="query" type="text" v-model="query">
              <button :aria-label="labels.submitSearch" type="submit" class="ui icon button">
                <i class="search icon"></i>
              </button>
            </div>
          </div>
        </form>
        <div class="ui secondary pointing menu">
          <a
            :class="['item', {active: type === t.id}]" 
            @click.prevent="type = t.id"
            v-for="t in types"
            href=""
            :key="t.id">
            {{ t.label }}
            <span
              v-if="results[t.id]"
              class="ui circular mini right floated label">
              {{ results[t.id].count }}</span>
            </a>
        </div>
        <div v-if="isLoading" >
          <div v-if="isLoading" class="ui inverted active dimmer">
            <div class="ui loader"></div>
          </div>
        </div>
    
        <empty-state v-else-if="!currentResults || currentResults.count === 0" @refresh="search" :refresh="true"></empty-state>
        
        <div v-else-if="type === 'artists'" class="ui five app-cards cards">
          <artist-card :artist="artist" v-for="artist in currentResults.results" :key="artist.id"></artist-card>
        </div>
        
        <div v-else-if="type === 'albums'" class="ui five app-cards cards">
          <album-card
            v-for="album in currentResults.results"
            :key="album.id"
            :album="album"></album-card>        
        </div>
        <track-table v-else-if="type === 'tracks'" :tracks="currentResults.results"></track-table>    
        <playlist-card-list v-else-if="type === 'playlists'"  :playlists="currentResults.results"></playlist-card-list>
        <div
          v-else-if="type === 'radios'"
          class="ui cards">
          <radio-card
            type="custom"
            v-for="radio in currentResults.results"
            :key="radio.id"
            :custom-radio="radio"></radio-card>
        </div>
        <tags-list
          v-else-if="type === 'tags'"
          :truncate-size="200"
          :limit="paginateBy"
          :tags="currentResults.results.map(t => {return t.name })"></tags-list>
      
        <pagination
          v-if="currentResults && currentResults.count > paginateBy"
          @page-changed="page = $event"
          :current="page"
          :paginate-by="paginateBy"
          :total="currentResults.count"
          ></pagination>
      
      </div>
    </section>
  </main>
</template>

<script>
import RemoteSearchForm from '@/components/RemoteSearchForm'
import ArtistCard from "@/components/audio/artist/Card"
import AlbumCard from "@/components/audio/album/Card"
import TrackTable from "@/components/audio/track/Table"
import Pagination from '@/components/Pagination'
import PlaylistCardList from "@/components/playlists/CardList"
import RadioCard from "@/components/radios/Card"
import TagsList from "@/components/tags/List"

import axios from 'axios'

export default {
  props: {
    initialId: { type: String, required: false},
    initialType: { type: String, required: false},
    initialQuery: { type: String, required: false},
    initialPage: { type: Number, required: false},
  },
  components: {
    RemoteSearchForm,
    ArtistCard,
    AlbumCard,
    TrackTable,
    Pagination,
    PlaylistCardList,
    RadioCard,
    TagsList,
  },
  data () {
    return {
      query: this.initialQuery,
      type: this.initialType,
      page: this.initialPage,
      results: {
        artists: null,
        albums: null,
        tracks: null,
        playlists: null,
        radios: null,
        tags: null,
      },
      isLoading: false,
      paginateBy: 25,
    }
  },
  created () {
    this.search()
  },
  computed: {
    labels() {
      let submitSearch = this.$pgettext("Content/Search/Button.Label/Verb", "Submit Search Query")
      let title = this.$pgettext("Content/Search/Input.Label/Noun", "Search")
      if (this.initialId) {
        title = this.$pgettext('Head/Fetch/Title', "Search a remote object")
        if (this.type === "rss") {
          title = this.$pgettext('Head/Fetch/Title', "Subscribe to a podcast RSS feed")
        }
      } 
      return {
        title,
        submitSearch
      }
    },
    types () {
      return [
        {
          id: 'artists',
          label: this.$pgettext("*/*/*/Noun", "Artists"),
        },
        {
          id: 'albums',
          label: this.$pgettext("*/*/*", "Albums"),
        },
        {
          id: 'tracks',
          label: this.$pgettext("*/*/*", "Tracks"),
        },
        {
          id: 'playlists',
          label: this.$pgettext("*/*/*", "Playlists"),
        },
        {
          id: 'radios',
          label: this.$pgettext("*/*/*", "Radios"),
          endpoint: 'radios/radios',
        },
        {
          id: 'tags',
          label: this.$pgettext("*/*/*", "Tags"),
        },
      ]
    },
    currentType () {
      return this.types.filter(t => {
        return t.id === this.type
      })[0]
    },
    currentResults () {
      return this.results[this.currentType.id]
    }
  },
  methods: {
    async search () {
      this.updateQueryString()
      if (!this.query) {
        this.types.forEach(t => {
          this.results[t.id] = null
        })
        return
      }
      this.isLoading = true
      let response = await axios.get(
        this.currentType.endpoint || this.currentType.id,
        {params: {q: this.query, page: this.page, page_size: this.paginateBy}}
      )
      this.results[this.currentType.id] = response.data
      this.isLoading = false
      this.types.forEach(t => {
        if (t.id != this.currentType.id) {
          axios.get(t.endpoint || t.id, {params: {q: this.query, page_size: 1}}).then(response => {
            this.results[t.id] = response.data
          })
        }
      })
    },
    updateQueryString: function() {
      history.pushState(
        {},
        null,
        this.$route.path + '?' + new URLSearchParams(
          {
          q: this.query,
          page: this.page,
          type: this.type,
        }).toString()
      )
    },
  },
  watch: {
    async type () {
      this.page = 1
      this.updateQueryString()
      await this.search()
    },
    async page () {
      this.updateQueryString()
      await this.search()
    }
  }
}
</script>
