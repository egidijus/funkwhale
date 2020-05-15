<template>
  <main v-title="labels.title">
    <section class="ui vertical stripe segment">
      <h2 class="ui header">
        <span class="ui circular huge hashtag label component-label">
          {{ labels.title }}
        </span>
      </h2>
      <radio-button type="tag" :object-id="id"></radio-button>
      <router-link class="ui right floated button" v-if="$store.state.auth.availablePermissions['library']" :to="{name: 'manage.library.tags.detail', params: {id: id}}">
        <i class="wrench icon"></i>
        <translate translate-context="Content/Moderation/Link">Open in moderation interface</translate>
      </router-link>

      <div class="ui hidden divider"></div>
      <div class="ui row">
        <artist-widget :key="id" :controls="false" :filters="{playable: true, ordering: '-creation_date', tag: id, include_channels: 'false'}">
          <template slot="title">
            <router-link :to="{name: 'library.artists.browse', query: {tag: id}}">
              <translate translate-context="*/*/*/Noun">Artists</translate>
            </router-link>
          </template>
        </artist-widget>
        <div class="ui hidden divider"></div>
        <div class="ui hidden divider"></div>
        <h3 class="ui header">
          <translate translate-context="*/*/*">Channels</translate>
        </h3>
        <channels-widget :key="id" :show-modification-date="true" :limit="12" :filters="{tag: id, ordering: '-creation_date'}"></channels-widget>
        <div class="ui hidden divider"></div>
        <div class="ui hidden divider"></div>
        <album-widget :key="id" :show-count="true" :controls="false" :filters="{playable: true, ordering: '-creation_date', tag: id}">
          <template slot="title">
            <router-link :to="{name: 'library.albums.browse', query: {tag: id}}">
              <translate translate-context="*/*/*">Albums</translate>
            </router-link>
          </template>
        </album-widget>
        <div class="ui hidden divider"></div>
        <div class="ui hidden divider"></div>
        <track-widget :key="id" :show-count="true" :limit="12" item-classes="track-item inline" :url="'/tracks/'" :is-activity="false" :filters="{playable: true, ordering: '-creation_date', tag: id}">
          <template slot="title">
            <translate translate-context="*/*/*">Tracks</translate>
          </template>
        </track-widget>
        <div class="ui clearing hidden divider"></div>
      </div>
    </section>
  </main>
</template>

<script>
import ChannelsWidget from "@/components/audio/ChannelsWidget"
import TrackWidget from "@/components/audio/track/Widget"
import AlbumWidget from "@/components/audio/album/Widget"
import ArtistWidget from "@/components/audio/artist/Widget"
import RadioButton from "@/components/radios/Button"

export default {
  props: {
    id: { type: String, required: true }
  },
  components: {
    ArtistWidget,
    AlbumWidget,
    TrackWidget,
    RadioButton,
    ChannelsWidget,
  },
  computed: {
    labels() {
      let title = `#${this.id}`
      return {
        title
      }
    },
    isAuthenticated () {
      return this.$store.state.auth.authenticated
    },
    hasFavorites () {
      return this.$store.state.favorites.count > 0
    },
  },
}
</script>
