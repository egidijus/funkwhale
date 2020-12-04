<template>
  <section>
    <div class="ui info message" v-if="pendingUploads.length > 0">
      <template v-if="isSuccessfull">
        <i role="button" class="close icon" @click="pendingUploads = []"></i>
        <h3 class="ui header">
          <translate translate-context="Content/Channel/Header">Uploads published successfully</translate>
        </h3>
        <p>
          <translate translate-context="Content/Channel/Paragraph">Processed uploads:</translate> {{ processedUploads.length }}/{{ pendingUploads.length }}
        </p>
      </template>
      <template v-else-if="isOver">
        <h3 class="ui header">
          <translate translate-context="Content/Channel/Header">Some uploads couldn't be published</translate>
        </h3>
        <div class="ui hidden divider"></div>
        <router-link
          class="ui basic button"
          :to="{name: 'content.libraries.files', query: {q: 'status:skipped'}}"
          v-if="skippedUploads.length > 0">
          <translate translate-context="Content/Channel/Button">View skipped uploads</translate>
        </router-link>
        <router-link
          class="ui basic button"
          :to="{name: 'content.libraries.files', query: {q: 'status:errored'}}"
          v-if="erroredUploads.length > 0">
          <translate translate-context="Content/Channel/Button">View errored uploads</translate>
        </router-link>
      </template>
      <template v-else>
        <div class="ui inline right floated active loader"></div>
        <h3 class="ui header">
          <translate translate-context="Content/Channel/Header">Uploads are being processed</translate>
        </h3>
        <p>
          <translate translate-context="Content/Channel/Paragraph">Your uploads are being processed by Funkwhale and will be live very soon.</translate>
        </p>
        <p>
          <translate translate-context="Content/Channel/Paragraph">Processed uploads:</translate> {{ processedUploads.length }}/{{ pendingUploads.length }}
        </p>

      </template>
    </div>
    <div v-if="$store.getters['ui/layoutVersion'] === 'small'">
      <rendered-description
        :content="object.artist.description"
        :update-url="`channels/${object.uuid}/`"
        :can-update="false"></rendered-description>
        <div class="ui hidden divider"></div>
    </div>
    <channel-entries :key="String(episodesKey) + 'entries'" :default-cover='object.artist.cover' :limit='25' :filters="{channel: object.uuid, ordering: '-creation_date', page_size: '25'}">
      <h2 class="ui header">
        <translate key="1" v-if="isPodcast" translate-context="Content/Channel/Paragraph">Latest episodes</translate>
        <translate key="2" v-else translate-context="Content/Channel/Paragraph">Latest tracks</translate>
      </h2>
    </channel-entries>
    <div class="ui hidden divider"></div>
    <channel-series :key="String(seriesKey) + 'series'" :filters="seriesFilters" :is-podcast="isPodcast">
      <h2 class="ui with-actions header">

        <translate key="1" v-if="isPodcast" translate-context="Content/Channel/Paragraph">Series</translate>
        <translate key="2" v-else translate-context="*/*/*">Albums</translate>
        <div class="actions" v-if="isOwner">
          <a @click.stop.prevent="$refs.albumModal.show = true">
            <i class="plus icon"></i>
            <translate translate-context="Content/Profile/Button">Add new</translate>
          </a>
        </div>
      </h2>
    </channel-series>
    <album-modal
      ref="albumModal"
      v-if="isOwner"
      :channel="object"
      @created="$refs.albumModal.show = false; seriesKey = new Date()"></album-modal>
  </section>
</template>

<script>
import axios from 'axios'
import qs from 'qs'

import ChannelEntries from "@/components/audio/ChannelEntries"
import ChannelSeries from "@/components/audio/ChannelSeries"
import AlbumModal from "@/components/channels/AlbumModal"


export default {
  props: ['object'],
  components: {
    ChannelEntries,
    ChannelSeries,
    AlbumModal,
  },
  data () {
    return {
      seriesKey: new Date(),
      episodesKey: new Date(),
      pendingUploads: [],
    }
  },
  async created () {
    if (this.isOwner) {
      await this.fetchPendingUploads()
      this.$store.commit("ui/addWebsocketEventHandler", {
        eventName: "import.status_updated",
        id: "fileUploadChannel",
        handler: this.handleImportEvent
      });
    }
  },
  destroyed() {
    this.$store.commit("ui/removeWebsocketEventHandler", {
      eventName: "import.status_updated",
      id: "fileUploadChannel"
    });
  },
  computed: {
    isPodcast () {
      return this.object.artist.content_category === 'podcast'
    },
    isOwner () {
      return this.$store.state.auth.authenticated && this.object.attributed_to.full_username === this.$store.state.auth.fullUsername
    },
    seriesFilters () {
      let filters = {artist: this.object.artist.id, ordering: '-creation_date'}
      if (!this.isOwner) {
        filters.playable = 'true'
      }
      return filters
    },
    processedUploads () {
      return this.pendingUploads.filter((u) => {
        return u.import_status != "pending"
      })
    },
    erroredUploads () {
      return this.pendingUploads.filter((u) => {
        return u.import_status === "errored"
      })
    },
    skippedUploads () {
      return this.pendingUploads.filter((u) => {
        return u.import_status === "skipped"
      })
    },
    finishedUploads () {
      return this.pendingUploads.filter((u) => {
        return u.import_status === "finished"
      })
    },
    pendingUploadsById () {
      let d = {}
      this.pendingUploads.forEach((u) => {
        d[u.uuid] = u
      })
      return d
    },
    isOver () {
      return this.pendingUploads && this.processedUploads.length === this.pendingUploads.length
    },
    isSuccessfull () {
      return this.pendingUploads && this.finishedUploads.length === this.pendingUploads.length
    }
  },
  methods: {
    handleImportEvent(event) {
      let self = this;
      if (!this.pendingUploadsById[event.upload.uuid]) {
        return;
      }
      Object.assign(this.pendingUploadsById[event.upload.uuid], event.upload)
    },
    async fetchPendingUploads () {
      let response = await axios.get('uploads/', {
        params: {channel: this.object.uuid, import_status: ['pending', 'skipped', 'errored'], include_channels: 'true'},
        paramsSerializer: function(params) {
          return qs.stringify(params, { indices: false })
        }
      })
      this.pendingUploads = response.data.results
    }
  },
  watch: {
    "$store.state.channels.latestPublication" (v) {
      if (v && v.uploads && v.channel.uuid === this.object.uuid) {
        let test
        this.pendingUploads = [...this.pendingUploads, ...v.uploads]
      }
    },
    "isOver" (v) {
      if (v) {
        this.seriesKey = new Date()
        this.episodesKey = new Date()
      }
    }
  }
}
</script>
