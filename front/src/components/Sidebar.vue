<template>
<aside :class="['ui', 'vertical', 'left', 'visible', 'wide', {'collapsed': isCollapsed}, 'sidebar', 'component-sidebar']">
  <header class="ui basic segment header-wrapper">
    <router-link :title="'Funkwhale'" :to="{name: logoUrl}">
      <i class="logo bordered inverted vibrant big icon">
        <logo class="logo"></logo>
        <span class="visually-hidden">Home</span>
      </i>
    </router-link>
    <router-link v-if="!$store.state.auth.authenticated" class="logo-wrapper" :to="{name: logoUrl}" :title="'Funkwhale'">
      <img src="../assets/logo/text-white.svg" alt="" />
    </router-link>
    <nav class="top ui compact right aligned inverted text menu">
      <template v-if="$store.state.auth.authenticated">

        <div class="right menu">
          <div class="item" :title="labels.administration" v-if="$store.state.auth.availablePermissions['settings'] || $store.state.auth.availablePermissions['moderation']">
            <div class="item ui inline admin-dropdown dropdown">
              <i class="wrench icon"></i>
              <div
                v-if="moderationNotifications > 0"
                :class="['ui', 'accent', 'mini', 'bottom floating', 'circular', 'label']">{{ moderationNotifications }}</div>
              <div class="menu">
                <h3 class="header">
                  <translate translate-context="Sidebar/Admin/Title/Noun">Administration</translate>
                </h3>
                <div class="divider"></div>
                <router-link
                  v-if="$store.state.auth.availablePermissions['library']"
                  class="item"
                  :to="{name: 'manage.library.edits', query: {q: 'is_approved:null'}}">
                  <div
                    v-if="$store.state.ui.notifications.pendingReviewEdits > 0"
                    :title="labels.pendingReviewEdits"
                    :class="['ui', 'circular', 'mini', 'right floated', 'accent', 'label']">
                    {{ $store.state.ui.notifications.pendingReviewEdits }}</div>
                  <translate translate-context="*/*/*/Noun">Library</translate>
                </router-link>
                <router-link
                  v-if="$store.state.auth.availablePermissions['moderation']"
                  class="item"
                  :to="{name: 'manage.moderation.reports.list', query: {q: 'resolved:no'}}">
                  <div
                    v-if="$store.state.ui.notifications.pendingReviewReports + $store.state.ui.notifications.pendingReviewRequests> 0"
                    :title="labels.pendingReviewReports"
                    :class="['ui', 'circular', 'mini', 'right floated', 'accent', 'label']">{{ $store.state.ui.notifications.pendingReviewReports + $store.state.ui.notifications.pendingReviewRequests }}</div>
                  <translate translate-context="*/Moderation/*">Moderation</translate>
                </router-link>
                <router-link
                  v-if="$store.state.auth.availablePermissions['settings']"
                  class="item"
                  :to="{name: 'manage.users.users.list'}">
                  <translate translate-context="*/*/*/Noun">Users</translate>
                </router-link>
                <router-link
                  v-if="$store.state.auth.availablePermissions['settings']"
                  class="item"
                  :to="{path: '/manage/settings'}">
                  <translate translate-context="*/*/*/Noun">Settings</translate>
                </router-link>
              </div>
            </div>
          </div>
        </div>
        <router-link
          class="item"
          v-if="$store.state.auth.authenticated"
          :to="{name: 'content.index'}">
        <i class="upload icon"></i>
        <span class="visually-hidden">{{ labels.addContent }}</span>
        </router-link>
        <router-link class="item" v-if="$store.state.auth.authenticated" :to="{name: 'notifications'}">
          <i class="bell icon"></i>
          <div v-if="$store.state.ui.notifications.inbox + additionalNotifications > 0" :class="['ui', 'accent', 'mini', 'bottom floating', 'circular', 'label']">
            {{ $store.state.ui.notifications.inbox + additionalNotifications }}
          </div>
          <span v-else class="visually-hidden">{{ labels.notifications }}</span>
        </router-link>
        <div class="item">
          <div class="ui user-dropdown dropdown" >
            <img class="ui avatar image" alt="" v-if="$store.state.auth.profile.avatar && $store.state.auth.profile.avatar.urls.medium_square_crop" :src="$store.getters['instance/absoluteUrl']($store.state.auth.profile.avatar.urls.medium_square_crop)" />
            <actor-avatar v-else :actor="{preferred_username: $store.state.auth.username, full_username: $store.state.auth.username}" />
            <div class="menu">
              <router-link class="item" :to="{name: 'profile.overview', params: {username: $store.state.auth.username}}"><translate translate-context="*/*/*/Noun">Profile</translate></router-link>
              <router-link class="item" :to="{path: '/settings'}"><translate translate-context="*/*/*/Noun">Settings</translate></router-link>
              <router-link class="item" :to="{name: 'logout'}"><translate translate-context="Sidebar/Login/List item.Link/Verb">Logout</translate></router-link>
            </div>
          </div>
        </div>
      </template>
      <div class="item collapse-button-wrapper">

        <button
          @click="isCollapsed = !isCollapsed"
          :class="['ui', 'basic', 'big', {'vibrant': !isCollapsed}, 'inverted icon', 'collapse', 'button']">
            <i class="sidebar icon"></i></button>
      </div>
    </nav>
  </header>
  <div class="ui basic search-wrapper segment">
    <search-bar @search="isCollapsed = false"></search-bar>
  </div>
  <div v-if="!$store.state.auth.authenticated" class="ui basic signup segment">
    <router-link class="ui fluid tiny primary button" :to="{name: 'login'}"><translate translate-context="*/Login/*/Verb">Login</translate></router-link>
    <div class="ui small hidden divider"></div>
    <router-link class="ui fluid tiny button" :to="{path: '/signup'}">
      <translate translate-context="*/Signup/Link/Verb">Create an account</translate>
    </router-link>
  </div>
  <nav class="secondary" role="navigation" aria-labelledby="navigation-label">
    <h1 id="navigation-label" class="visually-hidden">
      <translate translate-context="*/*/*">Main navigation</translate>
    </h1>
    <div class="ui small hidden divider"></div>
    <section :class="['ui', 'bottom', 'attached', {active: selectedTab === 'library'}, 'tab']" :aria-label="labels.mainMenu">
      <nav class="ui vertical large fluid inverted menu" role="navigation" :aria-label="labels.mainMenu">
        <div :class="[{collapsed: !exploreExpanded}, 'collapsible item']">
          <h2 class="header" role="button" @click="exploreExpanded = true" tabindex="0" @focus="exploreExpanded = true">
            <translate translate-context="*/*/*/Verb">Explore</translate>
            <i class="angle right icon" v-if="!exploreExpanded"></i>
          </h2>
          <div class="menu">
            <router-link class="item" :to="{name: 'search'}"><i class="search icon"></i><translate translate-context="Sidebar/Navigation/List item.Link/Verb">Search</translate></router-link>
            <router-link class="item" :exact="true" :to="{name: 'library.index'}"><i class="music icon"></i><translate translate-context="Sidebar/Navigation/List item.Link/Verb">Browse</translate></router-link>
            <router-link class="item" :to="{name: 'library.podcasts.browse'}"><i class="podcast icon"></i><translate translate-context="*/*/*">Podcasts</translate></router-link>
            <router-link class="item" :to="{name: 'library.albums.browse'}"><i class="compact disc icon"></i><translate translate-context="*/*/*">Albums</translate></router-link>
            <router-link class="item" :to="{name: 'library.artists.browse'}"><i class="user icon"></i><translate translate-context="*/*/*">Artists</translate></router-link>
            <router-link class="item" :to="{name: 'library.playlists.browse'}"><i class="list icon"></i><translate translate-context="*/*/*">Playlists</translate></router-link>
            <router-link class="item" :to="{name: 'library.radios.browse'}"><i class="feed icon"></i><translate translate-context="*/*/*">Radios</translate></router-link>
          </div>
        </div>
        <div :class="[{collapsed: !myLibraryExpanded}, 'collapsible item']" v-if="$store.state.auth.authenticated">
          <h3 class="header" role="button" @click="myLibraryExpanded = true" tabindex="0" @focus="myLibraryExpanded = true">
            <translate translate-context="*/*/*/Noun">My Library</translate>
            <i class="angle right icon" v-if="!myLibraryExpanded"></i>
          </h3>
          <div class="menu">
            <router-link class="item" :exact="true" :to="{name: 'library.me'}"><i class="music icon"></i><translate translate-context="Sidebar/Navigation/List item.Link/Verb">Browse</translate></router-link>
            <router-link class="item" :to="{name: 'library.albums.me'}"><i class="compact disc icon"></i><translate translate-context="*/*/*">Albums</translate></router-link>
            <router-link class="item" :to="{name: 'library.artists.me'}"><i class="user icon"></i><translate translate-context="*/*/*">Artists</translate></router-link>
            <router-link class="item" :to="{name: 'library.playlists.me'}"><i class="list icon"></i><translate translate-context="*/*/*">Playlists</translate></router-link>
            <router-link class="item" :to="{name: 'library.radios.me'}"><i class="feed icon"></i><translate translate-context="*/*/*">Radios</translate></router-link>
            <router-link class="item" :to="{name: 'favorites'}"><i class="heart icon"></i><translate translate-context="Sidebar/Favorites/List item.Link/Noun">Favorites</translate></router-link>
          </div>
        </div>
        <router-link class="header item" :to="{name: 'subscriptions'}" v-if="$store.state.auth.authenticated">
          <translate translate-context="*/*/*">Channels</translate>
        </router-link>
        <div class="item">
          <h3 class="header">
            <translate translate-context="Footer/About/List item.Link">More</translate>
          </h3>
          <div class="menu">
            <router-link class="item" to="/about">
              <i class="info icon"></i><translate translate-context="Sidebar/*/List item.Link">About this pod</translate>
            </router-link>
          </div>
        </div>
      </nav>
    </section>
  </nav>
</aside>
</template>

<script>
import { mapState, mapActions, mapGetters } from "vuex"

import Logo from "@/components/Logo"
import SearchBar from "@/components/audio/SearchBar"

import $ from "jquery"

export default {
  name: "sidebar",
  components: {
    SearchBar,
    Logo
  },
  data() {
    return {
      selectedTab: "library",
      isCollapsed: true,
      fetchInterval: null,
      exploreExpanded: false,
      myLibraryExpanded: false,
    }
  },
  destroy() {
    if (this.fetchInterval) {
      clearInterval(this.fetchInterval)
    }
  },
  mounted () {
    this.$nextTick(() => {
      document.getElementById('fake-sidebar').classList.add('loaded')
    })
  },
  computed: {
    ...mapGetters({
      additionalNotifications: "ui/additionalNotifications",
    }),
    ...mapState({
      queue: state => state.queue,
      url: state => state.route.path
    }),
    labels() {
      let mainMenu = this.$pgettext('Sidebar/*/Hidden text', "Main menu")
      let selectTrack = this.$pgettext('Sidebar/Player/Hidden text', "Play this track")
      let pendingFollows = this.$pgettext('Sidebar/Notifications/Hidden text', "Pending follow requests")
      let pendingReviewEdits = this.$pgettext('Sidebar/Moderation/Hidden text', "Pending review edits")
      return {
        pendingFollows,
        mainMenu,
        selectTrack,
        pendingReviewEdits,
        addContent: this.$pgettext("*/Library/*/Verb", 'Add content'),
        notifications: this.$pgettext("*/Notifications/*", 'Notifications'),
        administration: this.$pgettext("Sidebar/Admin/Title/Noun", 'Administration'),
      }
    },
    logoUrl() {
      if (this.$store.state.auth.authenticated) {
        return "library.index"
      } else {
        return "index"
      }
    },
    focusedMenu () {
      let mapping = {
        "search": 'exploreExpanded',
        "library.index": 'exploreExpanded',
        "library.podcasts.browse": 'exploreExpanded',
        "library.albums.browse": 'exploreExpanded',
        "library.albums.detail": 'exploreExpanded',
        "library.artists.browse": 'exploreExpanded',
        "library.artists.detail": 'exploreExpanded',
        "library.tracks.detail": 'exploreExpanded',
        "library.playlists.browse": 'exploreExpanded',
        "library.playlists.detail": 'exploreExpanded',
        "library.radios.browse": 'exploreExpanded',
        "library.radios.detail": 'exploreExpanded',
        'library.me': "myLibraryExpanded",
        'library.albums.me': "myLibraryExpanded",
        'library.artists.me': "myLibraryExpanded",
        'library.playlists.me': "myLibraryExpanded",
        'library.radios.me': "myLibraryExpanded",
        'favorites': "myLibraryExpanded",
      }
      let m = mapping[this.$route.name]
      if (m) {
        return m
      }

      if (this.$store.state.auth.authenticated) {
        return 'myLibraryExpanded'
      } else {
        return 'exploreExpanded'
      }
    },
    moderationNotifications () {
      return (
        this.$store.state.ui.notifications.pendingReviewEdits +
        this.$store.state.ui.notifications.pendingReviewReports +
        this.$store.state.ui.notifications.pendingReviewRequests
      )
    }
  },
  methods: {
    ...mapActions({
      cleanTrack: "queue/cleanTrack"
    }),
    applyContentFilters () {
      let artistIds = this.$store.getters['moderation/artistFilters']().map((f) => {
        return f.target.id
      })

      if (artistIds.length === 0) {
        return
      }
      let self = this
      let tracks = this.tracks.slice().reverse()
      tracks.forEach(async (t, i) => {
        // we loop from the end because removing index from the start can lead to removing the wrong tracks
        let realIndex = tracks.length - i - 1
        let matchArtist = artistIds.indexOf(t.artist.id) > -1
        if (matchArtist) {
          return await self.cleanTrack(realIndex)
        }
        if (t.album && artistIds.indexOf(t.album.artist.id) > -1) {
          return await self.cleanTrack(realIndex)
        }
      })
    },
    setupDropdown (selector) {
      let self = this
      $(self.$el).find(selector).dropdown({
        selectOnKeydown: false,
        action: function (text, value, $el) {
          // used ton ensure focusing the dropdown and clicking via keyboard
          // works as expected
          let link = $($el).closest('a')
          let url = link.attr('href')
          self.$router.push(url)
          $(self.$el).find(selector).dropdown('hide')
        }
      })
    }
  },
  watch: {
    url: function() {
      this.isCollapsed = true
    },
    "$store.state.moderation.lastUpdate": function () {
      this.applyContentFilters()
    },
    "$store.state.auth.authenticated": {
      immediate: true,
      handler (v) {
        if (v) {
          this.$nextTick(() => {
            this.setupDropdown('.user-dropdown')
            this.setupDropdown('.admin-dropdown')
          })
        }
      }
    },
    "$store.state.auth.availablePermissions": {
      immediate: true,
      handler (v) {
        this.$nextTick(() => {
          this.setupDropdown('.admin-dropdown')
        })
      },
      deep: true,
    },
    focusedMenu: {
      immediate: true,
      handler (n) {
        if (n) {
          this[n] = true
        }
      }
    },
    myLibraryExpanded (v) {
      if (v) {
        this.exploreExpanded = false
      }
    },
    exploreExpanded (v) {
      if (v) {
        this.myLibraryExpanded = false
      }
    },
  }
}
</script>
