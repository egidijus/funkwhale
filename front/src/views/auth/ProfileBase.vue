<template>
  <main class="main pusher page-profile" v-title="labels.usernameProfile">
    <div v-if="isLoading" class="ui vertical segment">
      <div class="ui centered active inline loader"></div>
    </div>
    <div class="ui head vertical stripe segment container">
      <div class="ui stackable grid" v-if="object">
        <div class="ui five wide column">
          <button class="ui pointing dropdown icon small basic right floated button" ref="dropdown" v-dropdown="{direction: 'downward'}" style="position: absolute; right: 1em; top: 1em;">
            <i class="ellipsis vertical icon"></i>
            <div class="menu">
              <div
                role="button"
                class="basic item"
                v-for="obj in getReportableObjs({account: object})"
                :key="obj.target.type + obj.target.id"
                @click.stop.prevent="$store.dispatch('moderation/report', obj.target)">
                <i class="share icon" /> {{ obj.label }}
              </div>

              <div class="divider"></div>
              <router-link class="basic item" v-if="$store.state.auth.availablePermissions['moderation']" :to="{name: 'manage.moderation.accounts.detail', params: {id: object.full_username}}">
                <i class="wrench icon"></i>
                <translate translate-context="Content/Moderation/Link">Open in moderation interface</translate>
              </router-link>
            </div>
          </button>
          <h1 class="ui center aligned icon header">
            <i v-if="!object.icon" class="circular inverted user success icon"></i>
            <img alt="" class="ui big circular image" v-else v-lazy="$store.getters['instance/absoluteUrl'](object.icon.urls.medium_square_crop)" />
            <div class="ellispsis content">
              <div class="ui very small hidden divider"></div>
              <span>{{ displayName }}</span>
              <div class="ui very small hidden divider"></div>
              <div class="sub header ellipsis" :title="object.full_username">
                {{ object.full_username }}
              </div>
            </div>
            <template  v-if="object.full_username === $store.state.auth.fullUsername">
              <div class="ui very small hidden divider"></div>
              <div class="ui basic success label">
                <translate translate-context="Content/Profile/Button.Paragraph">This is you!</translate>
              </div>
            </template>
          </h1>
          <div class="ui small hidden divider"></div>
          <div v-if="$store.getters['ui/layoutVersion'] === 'large'">
            <rendered-description
              @updated="$emit('updated', $event)"
              :content="object.summary"
              :field-name="'summary'"
              :update-url="`users/${$store.state.auth.username}/`"
              :can-update="$store.state.auth.authenticated && object.full_username === $store.state.auth.fullUsername"></rendered-description>
          </div>
        </div>
        <div class="ui eleven wide column">
          <div class="ui head vertical stripe segment">
            <div class="ui container">
              <div class="ui secondary pointing center aligned menu">
                <router-link class="item" :exact="true" :to="{name: 'profile.overview', params: routerParams}">
                  <translate translate-context="Content/Profile/Link">Overview</translate>
                </router-link>
                <router-link class="item" :exact="true" :to="{name: 'profile.activity', params: routerParams}">
                  <translate translate-context="Content/Profile/*">Activity</translate>
                </router-link>
              </div>
              <div class="ui hidden divider"></div>
              <router-view @updated="fetch" :object="object"></router-view>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<script>
import { mapState } from "vuex"
import axios from 'axios'

import ReportMixin from '@/components/mixins/Report'

export default {
  mixins: [ReportMixin],
  props: {
    username: {type: String, required: true},
    domain: {type: String, required: false, default: null},
  },
  data () {
    return {
      object: null,
      isLoading: false,
    }
  },
  created() {
    this.fetch()
  },
  beforeRouteUpdate (to, from, next) {
    to.meta.preserveScrollPosition = true
    next()
  },
  methods: {
    fetch () {
      let self = this
      self.object = null
      self.isLoading = true
      axios.get(`federation/actors/${this.fullUsername}/`).then((response) => {
        self.object = response.data
        self.isLoading = false
      })
    }
  },
  computed: {
    labels() {
      let msg = this.$pgettext('Head/Profile/Title', "%{ username }'s profile")
      let usernameProfile = this.$gettextInterpolate(msg, {
        username: this.username
      })
      return {
        usernameProfile
      }
    },
    fullUsername () {
      if (this.username && this.domain) {
        return `${this.username}@${this.domain}`
      } else {
        return `${this.username}@${this.$store.getters['instance/domain']}`
      }
    },
    routerParams () {
      if (this.domain) {
        return {username: this.username, domain: this.domain}
      } else {
        return {username: this.username}
      }
    },
    displayName () {
      return this.object.name || this.object.preferred_username
    }
  },
  watch: {
    domain () {
      this.fetch()
    },
    username () {
      this.fetch()
    }
  }
}
</script>
