<template>
  <span>

    <modal v-if="isEmbedable" :show.sync="showEmbedModal">
      <div class="header">
        <translate translate-context="Popup/Album/Title/Verb">Embed this album on your website</translate>
      </div>
      <div class="scrolling content">
        <div class="description">
          <embed-wizard type="album" :id="object.id" />

        </div>
      </div>
      <div class="actions">
        <div class="ui basic deny button">
          <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
        </div>
      </div>
    </modal>
    <div role="button" class="ui floating dropdown circular icon basic button" :title="labels.more" v-dropdown="{direction: 'downward'}">
      <i class="ellipsis vertical icon"></i>
      <div class="menu">
        <div
          role="button"
          v-if="isEmbedable"
          @click="showEmbedModal = !showEmbedModal"
          class="basic item">
          <i class="code icon"></i>
          <translate translate-context="Content/*/Button.Label/Verb">Embed</translate>
        </div>
        <a v-if="isAlbum && musicbrainzUrl" :href="musicbrainzUrl" target="_blank" rel="noreferrer noopener" class="basic item">
          <i class="external icon"></i>
          <translate translate-context="Content/*/*/Clickable, Verb">View on MusicBrainz</translate>
        </a>
        <a v-if="!isChannel && isAlbum" :href="discogsUrl" target="_blank" rel="noreferrer noopener" class="basic item">
          <i class="external icon"></i>
          <translate translate-context="Content/*/Button.Label/Verb">Search on Discogs</translate>
                    </a>
        <router-link
          v-if="object.is_local"
          :to="{name: 'library.albums.edit', params: {id: object.id }}"
          class="basic item">
          <i class="edit icon"></i>
          <translate translate-context="Content/*/Button.Label/Verb">Edit</translate>
        </router-link>
        <dangerous-button
          :class="['ui', {loading: isLoading}, 'item']"
          v-if="artist && $store.state.auth.authenticated && artist.channel && artist.attributed_to.full_username === $store.state.auth.fullUsername"
          @confirm="remove()">
          <i class="ui trash icon"></i>
          <translate translate-context="*/*/*/Verb">Delete…</translate>
          <p slot="modal-header"><translate translate-context="Popup/Channel/Title">Delete this album?</translate></p>
          <div slot="modal-content">
            <p><translate translate-context="Content/Moderation/Paragraph">The album will be deleted, as well as any related files and data. This action is irreversible.</translate></p>
          </div>
          <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
        </dangerous-button>
        <div class="divider"></div>
        <div
          role="button"
          class="basic item"
          v-for="obj in getReportableObjs({album: object, channel: artist.channel})"
          :key="obj.target.type + obj.target.id"
          @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
          <i class="share icon" /> {{ obj.label }}
        </div>
        <div class="divider"></div>
        <router-link class="basic item" v-if="$store.state.auth.availablePermissions['library']" :to="{name: 'manage.library.albums.detail', params: {id: object.id}}">
          <i class="wrench icon"></i>
          <translate translate-context="Content/Moderation/Link">Open in moderation interface</translate>
        </router-link>
        <a
          v-if="$store.state.auth.profile && $store.state.auth.profile.is_superuser"
          class="basic item"
          :href="$store.getters['instance/absoluteUrl'](`/api/admin/music/album/${object.id}`)"
          target="_blank" rel="noopener noreferrer">
          <i class="wrench icon"></i>
          <translate translate-context="Content/Moderation/Link/Verb">View in Django's admin</translate>&nbsp;
        </a>
      </div>
    </div>
  </span>
</template>
<script>
import EmbedWizard from "@/components/audio/EmbedWizard"
import Modal from '@/components/semantic/Modal'
import ReportMixin from '@/components/mixins/Report'


export default {
  mixins: [ReportMixin],
  props: {
    isLoading: Boolean,
    artist: Object,
    object: Object,
    publicLibraries: Array,
    isAlbum: Boolean,
    isChannel: Boolean,
    isSerie: Boolean,
  },
  components: {
    EmbedWizard,
    Modal,
  },
  data () {
    return {
      showEmbedModal: false,
    }
  },
  computed: {
    labels() {
      return {
        more: this.$pgettext('*/*/Button.Label/Noun', "More…"),
      }
    },
    isEmbedable () {
      return (this.isChannel && this.artist.channel.actor) || this.publicLibraries.length > 0
    },

    musicbrainzUrl() {
      if (this.object.mbid) {
        return "https://musicbrainz.org/release/" + this.object.mbid
      }
    },
    discogsUrl() {
      return (
        "https://discogs.com/search/?type=release&title=" +
        encodeURI(this.object.title) + "&artist=" +
        encodeURI(this.object.artist.name)
      )
    },
  }
}
</script>
