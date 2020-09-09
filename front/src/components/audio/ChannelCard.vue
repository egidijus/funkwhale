<template>
  <div class="card app-card">
    <div
      @click="$router.push({name: 'channels.detail', params: {id: urlId}})"
      :class="['ui', 'head-image', {'circular': object.artist.content_category != 'podcast'}, {'padded': object.artist.content_category === 'podcast'}, 'image', {'default-cover': !object.artist.cover}]" v-lazy:background-image="imageUrl">
      <play-button :icon-only="true" :is-playable="true" :button-classes="['ui', 'circular', 'large', 'vibrant', 'icon', 'button']" :artist="object.artist"></play-button>
    </div>
    <div class="content">
      <strong>
        <router-link class="discrete link" :to="{name: 'channels.detail', params: {id: urlId}}">
          {{ object.artist.name }}
        </router-link>
      </strong>
      <div class="description">
        <translate class="meta ellipsis" translate-context="Content/Channel/Paragraph"
          key="1"
          v-if="object.artist.content_category === 'podcast'"
          translate-plural="%{ count } episodes"
          :translate-n="object.artist.tracks_count"
          :translate-params="{count: object.artist.tracks_count}">
          %{ count } episode
        </translate>
        <translate key="2" v-else translate-context="*/*/*" :translate-params="{count: object.artist.tracks_count}" :translate-n="object.artist.tracks_count" translate-plural="%{ count } tracks">%{ count } track</translate>
        <tags-list label-classes="tiny" :truncate-size="20" :limit="2" :show-more="false" :tags="object.artist.tags"></tags-list>
      </div>

    </div>
    <div class="extra content">
      <time
        v-translate
        class="meta ellipsis"
        :datetime="object.artist.modification_date"
        :title="updatedTitle">
        %{ updatedAgo }
      </time>
      <play-button
        class="right floated basic icon"
        :dropdown-only="true"
        :is-playable="true"
        :dropdown-icon-classes="['ellipsis', 'horizontal', 'large really discrete']" :artist="object.artist" :channel="object" :account="object.attributed_to"></play-button>
    </div>
  </div>
</template>

<script>
import PlayButton from '@/components/audio/PlayButton'
import TagsList from "@/components/tags/List"

import {momentFormat} from '@/filters'
import moment from "moment"

export default {
  props: {
    object: {type: Object},
  },
  components: {
    PlayButton,
    TagsList
  },
  computed: {
    imageUrl () {
      if (this.object.artist.cover) {
        return this.$store.getters['instance/absoluteUrl'](this.object.artist.cover.urls.medium_square_crop)
      }
    },
    urlId () {
      if (this.object.actor && this.object.actor.is_local) {
        return this.object.actor.preferred_username
      } else if (this.object.actor) {
        return this.object.actor.full_username
      } else {
        return this.object.uuid
      }
    },
    updatedTitle () {
      let d = momentFormat(this.object.artist.modification_date)
      let message = this.$pgettext('*/*/*', 'Updated on %{ date }')
      return this.$gettextInterpolate(message, {date: d})
    },
    updatedAgo () {
      return moment(this.object.artist.modification_date).fromNow()
    }
  }
}
</script>
