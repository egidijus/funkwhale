<template>
  <router-link class="artist-label ui image label" :to="route">
    <img alt="" :class="[{circular: artist.content_category != 'podcast'}]" v-if="artist.cover && artist.cover.urls.original" v-lazy="$store.getters['instance/absoluteUrl'](artist.cover.urls.medium_square_crop)" />
    <i :class="[artist.content_category != 'podcast' ? 'circular' : 'bordered', 'inverted violet users icon']" v-else />
    {{ artist.name }}
  </router-link>
</template>

<script>

import {momentFormat} from '@/filters'

export default {
  props: {
    artist: Object,
  },
  computed: {
    route () {
      if (this.artist.channel) {
        return {name: 'channels.detail', params: {id: this.artist.channel.uuid}}
      }
      return {name: 'library.artists.detail', params: {id: this.artist.id}}
    }
  }
}
</script>
