<template>
  <main class="main pusher" v-title="labels.title">
    <div v-if="isLoading" class="ui vertical segment">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <template v-if="object && !isLoading">
      <section class="ui head vertical stripe segment container" v-title="object.artist.name">
        <div class="ui stackable grid">
          <div class="seven wide column">
            <div class="ui two column grid">
              <div class="column">
                <img class="huge channel-image" v-if="object.artist.cover" :src="$store.getters['instance/absoluteUrl'](object.artist.cover.medium_square_crop)">
                <i v-else class="huge circular inverted users violet icon"></i>
              </div>
              <div class="ui column right aligned">
                <tags-list v-if="object.artist.tags && object.artist.tags.length > 0" :tags="object.artist.tags"></tags-list>
                <actor-link v-if="object.actor" :avatar="false" :actor="object.attributed_to" :display-name="true"></actor-link>
                <template v-if="totalTracks > 0">
                  <div class="ui hidden very small divider"></div>
                  <translate translate-context="Content/Channel/Paragraph"
                    key="1"
                    v-if="object.artist.content_category === 'podcast'"
                    translate-plural="%{ count } episodes"
                    :translate-n="totalTracks"
                    :translate-params="{count: totalTracks}">
                    %{ count } episode
                  </translate>
                  <translate key="2" v-else translate-context="*/*/*" :translate-params="{count: totalTracks}" :translate-n="totalTracks" translate-plural="%{ count } tracks">%{ count } track</translate>
                </template>
                <template v-if="object.attributed_to.full_username === $store.state.auth.fullUsername || $store.getters['channels/isSubscribed'](object.uuid)">
                  · <translate translate-context="Content/Channel/Paragraph" translate-plural="%{ count } subscribers" :translate-n="object.subscriptions_count" :translate-params="{count: object.subscriptions_count}">%{ count } subscriber</translate>
                </template>
                <div class="ui hidden small divider"></div>
                <a @click.stop.prevent="showSubscribeModal = true" class="ui icon small basic button">
                  <i class="feed icon"></i>
                </a>
                <modal class="tiny" :show.sync="showSubscribeModal">
                  <div class="header">
                    <translate translate-context="Popup/Channel/Title/Verb">Subscribe to this channel</translate>
                  </div>
                  <div class="scrollable content">
                    <div class="description">

                      <template v-if="$store.state.auth.authenticated">
                        <h3>
                          <i class="user icon"></i>
                          <translate translate-context="Content/Channels/Header">Subscribe on Funkwhale</translate>
                        </h3>
                        <subscribe-button @subscribed="object.subscriptions_count += 1" @unsubscribed="object.subscriptions_count -= 1" :channel="object"></subscribe-button>
                      </template>
                      <template v-if="object.rss_url">
                        <h3>
                          <i class="feed icon"></i>
                          <translate translate-context="Content/Channels/Header">Subscribe via RSS</translate>
                        </h3>
                        <p><translate translate-context="Content/Channels/Label">Copy-paste the following URL in your favorite podcasting app:</translate></p>
                        <copy-input :value="object.rss_url" />
                      </template>
                      <template v-if="object.actor">
                        <h3>
                          <i class="bell icon"></i>
                          <translate translate-context="Content/Channels/Header">Subscribe on the Fediverse</translate>
                        </h3>
                        <p><translate translate-context="Content/Channels/Label">If you're using Mastodon or other fediverse applications, you can subscribe to this account:</translate></p>
                        <copy-input :value="`@${object.actor.full_username}`" />
                      </template>
                    </div>
                  </div>
                  <div class="actions">
                    <div class="ui basic deny button">
                      <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
                    </div>
                  </div>
                </modal>
                <div class="ui right floated pointing dropdown icon small basic button" ref="dropdown" v-dropdown="{direction: 'downward'}">
                  <i class="ellipsis vertical icon"></i>
                  <div class="menu">
                    <div
                      role="button"
                      v-if="totalTracks > 0"
                      @click="showEmbedModal = !showEmbedModal"
                      class="basic item">
                      <i class="code icon"></i>
                      <translate translate-context="Content/*/Button.Label/Verb">Embed</translate>
                    </div>
                    <div class="divider"></div>
                    <div
                      role="button"
                      class="basic item"
                      v-for="obj in getReportableObjs({account: object.attributed_to, channel: object})"
                      :key="obj.target.type + obj.target.id"
                      @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
                      <i class="share icon" /> {{ obj.label }}
                    </div>

                    <template v-if="isOwner">
                      <div class="divider"></div>
                      <div
                        class="item"
                        role="button"
                        @click.stop="showEditModal = true">
                        <translate translate-context="*/*/*/Verb">Edit…</translate>
                      </div>
                      <dangerous-button
                        :class="['ui', {loading: isLoading}, 'item']"
                        v-if="object"
                        @confirm="remove()">
                        <translate translate-context="*/*/*/Verb">Delete…</translate>
                        <p slot="modal-header"><translate translate-context="Popup/Channel/Title">Delete this Channel?</translate></p>
                        <div slot="modal-content">
                          <p><translate translate-context="Content/Moderation/Paragraph">The channel will be deleted, as well as any related files and data. This action is irreversible.</translate></p>
                        </div>
                        <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
                      </dangerous-button>
                    </template>
                    <template v-if="$store.state.auth.availablePermissions['library']" >
                      <div class="divider"></div>
                      <router-link class="basic item" :to="{name: 'manage.channels.detail', params: {id: object.uuid}}">
                        <i class="wrench icon"></i>
                        <translate translate-context="Content/Moderation/Link">Open in moderation interface</translate>
                      </router-link>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            <h1 class="ui header">
              <div class="left aligned" :title="object.artist.name">
                {{ object.artist.name }}
                <div class="ui hidden very small divider"></div>
                <div class="sub header ellipsis" v-if="object.actor" :title="object.actor.full_username">
                  {{ object.actor.full_username }}
                </div>
                <div v-else class="sub header ellipsis">
                  <a :href="object.url || object.rss_url" rel="noopener noreferrer" target="_blank">
                    <i class="external link icon"></i>
                    <translate :translate-params="{domain: externalDomain}" translate-context="Content/Channel/Paragraph">Mirrored from %{ domain }</translate>
                  </a>
                </div>
              </div>
            </h1>
            <div class="header-buttons">
              <div class="ui buttons" v-if="isOwner">
                <button class="ui basic labeled icon button" @click.prevent.stop="$store.commit('channels/showUploadModal', {show: true, config: {channel: object}})">
                  <i class="upload icon"></i>
                  <translate translate-context="Content/Channels/Button.Label/Verb">Upload</translate>
                </button>
              </div>
              <div class="ui buttons">
                <play-button :is-playable="isPlayable" class="orange" :artist="object.artist">
                  <translate translate-context="Content/Channels/Button.Label/Verb">Play</translate>
                </play-button>
              </div>
              <div class="ui buttons">
                <subscribe-button @subscribed="object.subscriptions_count += 1" @unsubscribed="object.subscriptions_count -= 1" :channel="object"></subscribe-button>
              </div>

              <modal :show.sync="showEmbedModal" v-if="totalTracks > 0">
                <div class="header">
                  <translate translate-context="Popup/Artist/Title/Verb">Embed this artist work on your website</translate>
                </div>
                <div class="scrolling content">
                  <div class="description">
                    <embed-wizard type="artist" :id="object.artist.id" />
                  </div>
                </div>
                <div class="actions">
                  <div class="ui basic deny button">
                    <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
                  </div>
                </div>
              </modal>
              <modal :show.sync="showEditModal" v-if="isOwner">
                <div class="header">
                  <translate v-if="object.artist.content_category === 'podcast'" key="1" translate-context="Content/Channel/*">Podcast channel</translate>
                  <translate v-else key="2" translate-context="Content/Channel/*">Artist channel</translate>

                </div>
                <div class="scrolling content">
                  <channel-form
                    ref="editForm"
                    :object="object"
                    @loading="edit.isLoading = $event"
                    @submittable="edit.submittable = $event"
                    @updated="fetchData"></channel-form>
                    <div class="ui hidden divider"></div>
                </div>
                <div class="actions">
                  <div class="ui left floated basic deny button">
                    <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
                  </div>
                  <button @click.stop="$refs.editForm.submit" :class="['ui', 'primary', 'confirm', {loading: edit.isLoading}, 'button']" :disabled="!edit.submittable">
                    <translate translate-context="*/Channels/Button.Label">Update channel</translate>
                  </button>
                </div>
              </modal>
            </div>
            <div v-if="$store.getters['ui/layoutVersion'] === 'large'">
              <rendered-description
                @updated="object = $event"
                :content="object.artist.description"
                :update-url="`channels/${object.uuid}/`"
                :can-update="false"></rendered-description>
            </div>
          </div>
          <div class="nine wide column">
            <div class="ui secondary pointing center aligned menu">
              <router-link class="item" :exact="true" :to="{name: 'channels.detail', params: {id: id}}">
                <translate translate-context="Content/Channels/Link">Overview</translate>
              </router-link>
              <router-link class="item" :exact="true" :to="{name: 'channels.detail.episodes', params: {id: id}}">
                <translate key="1" v-if="isPodcast" translate-context="Content/Channels/*">Episodes</translate>
                <translate key="2" v-else translate-context="*/*/*">Tracks</translate>
              </router-link>
            </div>
            <div class="ui hidden divider"></div>
            <router-view v-if="object" :object="object" @tracks-loaded="totalTracks = $event"></router-view>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script>
import axios from "axios"
import PlayButton from "@/components/audio/PlayButton"
import ChannelEntries from "@/components/audio/ChannelEntries"
import ChannelSeries from "@/components/audio/ChannelSeries"
import EmbedWizard from "@/components/audio/EmbedWizard"
import Modal from '@/components/semantic/Modal'
import TagsList from "@/components/tags/List"
import ReportMixin from '@/components/mixins/Report'

import SubscribeButton from '@/components/channels/SubscribeButton'
import ChannelForm from "@/components/audio/ChannelForm"

export default {
  mixins: [ReportMixin],
  props: ["id"],
  components: {
    PlayButton,
    EmbedWizard,
    Modal,
    TagsList,
    ChannelEntries,
    ChannelSeries,
    SubscribeButton,
    ChannelForm,
  },
  data() {
    return {
      isLoading: true,
      object: null,
      totalTracks: 0,
      latestTracks: null,
      showEmbedModal: false,
      showEditModal: false,
      showSubscribeModal: false,
      edit: {
        submittable: false,
        loading: false,
      }
    }
  },
  beforeRouteUpdate (to, from, next) {
    to.meta.preserveScrollPosition = true
    next()
  },
  async created() {
    await this.fetchData()
  },
  methods: {
    async fetchData() {
      var self = this
      this.showEditModal = false
      this.edit.isLoading = false
      this.isLoading = true
      let channelPromise = axios.get(`channels/${this.id}`, {params: {refresh: 'true'}}).then(response => {
        self.object = response.data
        if ((self.id == response.data.uuid) && response.data.actor) {
          // replace with the pretty channel url if possible
          let actor = response.data.actor
          if (actor.is_local) {
            self.$router.replace({name: 'channels.detail', params: {id: actor.preferred_username}})
          } else {
            self.$router.replace({name: 'channels.detail', params: {id: actor.full_username}})
          }
        }
        let tracksPromise = axios.get("tracks", {params: {channel: response.data.uuid, page_size: 1, playable: true, include_channels: true}}).then(response => {
          self.totalTracks = response.data.count
          self.isLoading = false
        })
      })
      await channelPromise
    },
    remove () {
      let self = this
      self.isLoading = true
      axios.delete(`channels/${this.object.uuid}`).then((response) => {
        self.isLoading = false
        self.$emit('deleted')
        self.$router.push({name: 'profile.overview', params: {username: self.$store.state.auth.username}})
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  },
  computed: {
    externalDomain () {
      let parser = document.createElement('a')
      parser.href = this.object.url || this.object.rss_url
      return parser.hostname
    },

    isOwner () {
      return this.$store.state.auth.authenticated && this.object.attributed_to.full_username === this.$store.state.auth.fullUsername
    },
    isPodcast () {
      return this.object.artist.content_category === 'podcast'
    },
    labels () {
      return {
        title: this.$pgettext('*/*/*', 'Channel')
      }
    },
    contentFilter () {
      let self = this
      return this.$store.getters['moderation/artistFilters']().filter((e) => {
        return e.target.id === this.object.artist.id
      })[0]
    },
    isPlayable () {
      return this.totalTracks > 0
    },
  },
  watch: {
    id() {
      this.fetchData()
    }
  }
}
</script>
