<template>
  <div v-if="playlists.length > 0">
    <div class="ui app-cards cards">
      <playlist-card
        :playlist="playlist"
        v-for="playlist in playlists"
        :key="playlist.id"
      ></playlist-card>
    </div>
  </div>
</template>

<script>

import PlaylistCard from '@/components/playlists/Card'

export default {
  props: ['playlists'],
  components: {
    PlaylistCard
  }
}
</script>
