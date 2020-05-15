<template>
  <div class="wrapper">
    <h3 class="ui header">
      <slot name="title"></slot>
      <span v-if="showCount" class="ui tiny circular label">{{ count }}</span>
    </h3>
    <slot></slot>
    <inline-search-bar v-model="query" v-if="search" @search="albums = []; fetchData()"></inline-search-bar>
    <div class="ui hidden divider"></div>
    <div class="ui app-cards cards">
      <div v-if="isLoading" class="ui inverted active dimmer">
        <div class="ui loader"></div>
      </div>
      <album-card v-for="album in albums" :album="album" :key="album.id" />
    </div>
    <slot v-if="!isLoading && albums.length === 0" name="empty-state">
      <empty-state @refresh="fetchData" :refresh="true"></empty-state>
    </slot>
    <template v-if="nextPage">
      <div class="ui hidden divider"></div>
      <button v-if="nextPage" @click="fetchData(nextPage)" :class="['ui', 'basic', 'button']">
        <translate translate-context="*/*/Button,Label">Show more</translate>
      </button>
    </template>
  </div>
</template>

<script>
import axios from 'axios'
import AlbumCard from '@/components/audio/album/Card'

export default {
  props: {
    filters: {type: Object, required: true},
    controls: {type: Boolean, default: true},
    showCount: {type: Boolean, default: false},
    search: {type: Boolean, default: false},
    limit: {type: Number, default: 12},
  },
  components: {
    AlbumCard
  },
  data () {
    return {
      albums: [],
      count: 0,
      isLoading: false,
      errors: null,
      previousPage: null,
      nextPage: null,
      query: '',
    }
  },
  created () {
    this.fetchData()
  },
  methods: {
    fetchData (url) {
      url = url || 'albums/'
      this.isLoading = true
      let self = this
      let params = {q: this.query, ...this.filters}
      params.page_size = this.limit
      params.offset = this.offset
      axios.get(url, {params: params}).then((response) => {
        self.previousPage = response.data.previous
        self.nextPage = response.data.next
        self.isLoading = false
        self.albums = [...self.albums, ...response.data.results]
        self.count = response.data.count
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    },
    updateOffset (increment) {
      if (increment) {
        this.offset += this.limit
      } else {
        this.offset = Math.max(this.offset - this.limit, 0)
      }
    },
  },
  watch: {
    offset () {
      this.fetchData()
    },
    "$store.state.moderation.lastUpdate": function () {
      this.fetchData()
    }
  }
}
</script>
