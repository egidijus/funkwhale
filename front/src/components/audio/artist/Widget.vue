<template>
  <div class="wrapper">
    <h3 v-if="header" class="ui header">
      <slot name="title"></slot>
      <span class="ui tiny circular label">{{ count }}</span>
    </h3>
    <inline-search-bar v-model="query" v-if="search" @search="objects = []; fetchData()"></inline-search-bar>
    <div class="ui hidden divider"></div>
    <div class="ui five app-cards cards">
      <div v-if="isLoading" class="ui inverted active dimmer">
        <div class="ui loader"></div>
      </div>
      <artist-card :artist="artist" v-for="artist in objects" :key="artist.id"></artist-card>
    </div>
    <slot v-if="!isLoading && objects.length === 0" name="empty-state">
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
import ArtistCard from "@/components/audio/artist/Card"

export default {
  props: {
    filters: {type: Object, required: true},
    controls: {type: Boolean, default: true},
    header: {type: Boolean, default: true},
    search: {type: Boolean, default: false},
  },
  components: {
    ArtistCard,
  },
  data () {
    return {
      objects: [],
      limit: 12,
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
      url = url || 'artists/'
      this.isLoading = true
      let self = this
      let params = {q: this.query, ...this.filters}
      params.page_size = this.limit
      params.offset = this.offset
      axios.get(url, {params: params}).then((response) => {
        self.previousPage = response.data.previous
        self.nextPage = response.data.next
        self.isLoading = false
        self.objects = [...self.objects, ...response.data.results]
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
