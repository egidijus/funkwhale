<template>
  <section>
    <div>
      <radio-button v-if="recentActivity > 0" class="right floated" type="account" :object-id="{username: object.preferred_username, fullUsername: object.full_username}" :client-only="true"></radio-button>
      <h2 class="ui header">
        <translate translate-context="Content/Home/Title">Recently listened</translate>
      </h2>
      <div class="ui divider"></div>
      <track-widget
        @count="recentActivity = $event"
        :url="'history/listenings/'"
        :filters="{scope: `actor:${object.full_username}`, ordering: '-creation_date'}">
      </track-widget>
    </div>
    <div class="ui hidden divider"></div>
    <div>
      <h2 class="ui header">
        <translate translate-context="Content/Home/Title">Recently favorited</translate>
      </h2>
      <div class="ui divider"></div>
      <track-widget :url="'favorites/tracks/'" :filters="{scope: `actor:${object.full_username}`, ordering: '-creation_date'}"></track-widget>
    </div>
    <div class="ui hidden divider"></div>
    <div>
      <h2 class="ui header">
        <translate translate-context="*/*/*">Playlists</translate>
      </h2>
      <div class="ui divider"></div>
      <playlist-widget :url="'playlists/'" :filters="{scope: `actor:${object.full_username}`, playable: true, ordering: '-modification_date'}">
      </playlist-widget>
    </div>
  </section>
</template>

<script>
import TrackWidget from "@/components/audio/track/Widget"
import PlaylistWidget from "@/components/playlists/Widget"
import RadioButton from "@/components/radios/Button"

export default {
  props: ['object'],
  components: {TrackWidget, PlaylistWidget, RadioButton},
  data () {
    return {
      recentActivity: 0,
    }
  }
}
</script>
