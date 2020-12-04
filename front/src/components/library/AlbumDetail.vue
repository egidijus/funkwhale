<template>
  <div v-if="object">
    <h2 class="ui header">
      <translate key="1" v-if="isSerie" translate-context="Content/Channels/*">Episodes</translate>
      <translate key="2" v-else translate-context="*/*/*">Tracks</translate>
    </h2>
    <channel-entries v-if="artist.channel && isSerie" :limit="50" :filters="{channel: artist.channel.uuid, album: object.id, ordering: '-creation_date'}">
    </channel-entries>
    <template v-else-if="discs && discs.length > 1">
      <div v-for="tracks in discs" :key="tracks.disc_number">
        <div class="ui hidden divider"></div>
        <play-button class="right floated mini inverted vibrant" :tracks="tracks"></play-button>
        <translate
          tag="h3"
          :translate-params="{number: tracks[0].disc_number}"
          translate-context="Content/Album/"
        >Volume %{ number }</translate>
        <album-entries :tracks="tracks"></album-entries>
      </div>
    </template>
    <template v-else>
      <album-entries :tracks="object.tracks"></album-entries>
    </template>
    <div class="ui center aligned basic segment">
      <pagination
        v-if="!isSerie && object.tracks && totalTracks > paginateBy"
        @page-changed="updatePage"
        :current="page"
        :paginate-by="paginateBy"
        :total="totalTracks"
      ></pagination>
    </div>
    <template v-if="!artist.channel && !isSerie">
      <h2>
        <translate translate-context="Content/*/Title/Noun">User libraries</translate>
      </h2>
      <library-widget @loaded="$emit('libraries-loaded', $event)" :url="'albums/' + object.id + '/libraries/'">
        <translate slot="subtitle" translate-context="Content/Album/Paragraph">This album is present in the following libraries:</translate>
      </library-widget>
    </template>
  </div>
</template>

<script>

import time from "@/utils/time"
import axios from "axios"
import url from "@/utils/url"
import logger from "@/logging"
import LibraryWidget from "@/components/federation/LibraryWidget"
import TrackTable from "@/components/audio/track/Table"
import ChannelEntries from '@/components/audio/ChannelEntries'
import AlbumEntries from '@/components/audio/AlbumEntries'
import Pagination from "@/components/Pagination"
import PaginationMixin from "@/components/mixins/Pagination"
import PlayButton from "@/components/audio/PlayButton"

export default {
  props: ["object", "libraries", "discs", "isSerie", "artist", "page", "paginateBy", "totalTracks"],
  components: {
    LibraryWidget,
    AlbumEntries,
    ChannelEntries,
    TrackTable,
    Pagination,
    PlayButton
  },
  data() {
    return {
      time,
      id: this.object.id,
    }
  },
  methods: {
    updatePage: function(page) {
      this.$emit('page-changed', page)
    }
  },
}
</script>
