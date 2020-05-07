<template>
<aside :class="['ui', 'vertical', 'left', 'visible', 'wide', {'collapsed': isCollapsed}, 'sidebar',]">
  <header class="ui basic segment header-wrapper">
    <router-link :title="'Funkwhale'" :to="{name: logoUrl}">
      <i class="logo bordered inverted orange big icon">
        <logo class="logo"></logo>
      </i>
    </router-link>
    <router-link v-if="!$store.state.auth.authenticated" class="logo-wrapper" :to="{name: logoUrl}">
      <img src="../assets/logo/text-white.svg" />
    </router-link>
    <nav class="top ui compact right aligned inverted text menu">
      <template v-if="$store.state.auth.authenticated">

        <div class="right menu">
          <div class="item" :title="labels.administration" v-if="$store.state.auth.availablePermissions['settings'] || $store.state.auth.availablePermissions['moderation']">
            <div class="item ui inline admin-dropdown dropdown">
              <i class="wrench icon"></i>
              <div
                v-if="moderationNotifications > 0"
                :class="['ui', 'teal', 'mini', 'bottom floating', 'circular', 'label']">{{ moderationNotifications }}</div>
              <div class="menu">
                <div class="header">
                  <translate translate-context="Sidebar/Admin/Title/Noun">Administration</translate>
                </div>
                <div class="divider"></div>
                <router-link
                  v-if="$store.state.auth.availablePermissions['library']"
                  class="item"
                  :to="{name: 'manage.library.edits', query: {q: 'is_approved:null'}}">
                  <div
                    v-if="$store.state.ui.notifications.pendingReviewEdits > 0"
                    :title="labels.pendingReviewEdits"
                    :class="['ui', 'circular', 'mini', 'right floated', 'teal', 'label']">
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
                    :class="['ui', 'circular', 'mini', 'right floated', 'teal', 'label']">{{ $store.state.ui.notifications.pendingReviewReports + $store.state.ui.notifications.pendingReviewRequests }}</div>
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
          :title="labels.addContent"
          :to="{name: 'content.index'}"><i class="upload icon"></i></router-link>

        <router-link class="item" v-if="$store.state.auth.authenticated" :title="labels.notifications" :to="{name: 'notifications'}">
          <i class="bell icon"></i><div
            v-if="$store.state.ui.notifications.inbox + additionalNotifications > 0"
            :class="['ui', 'teal', 'mini', 'bottom floating', 'circular', 'label']">{{ $store.state.ui.notifications.inbox + additionalNotifications }}</div>
        </router-link>
        <div class="item">
          <div class="ui user-dropdown dropdown" >
            <img class="ui avatar image" v-if="$store.state.auth.profile.avatar && $store.state.auth.profile.avatar.square_crop" :src="$store.getters['instance/absoluteUrl']($store.state.auth.profile.avatar.square_crop)" />
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

        <span
          @click="isCollapsed = !isCollapsed"
          :class="['ui', 'basic', 'big', {'orange': !isCollapsed}, 'inverted icon', 'collapse', 'button']">
            <i class="sidebar icon"></i></span>
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
  <nav class="secondary" role="navigation">
    <div class="ui small hidden divider"></div>
    <section :class="['ui', 'bottom', 'attached', {active: selectedTab === 'library'}, 'tab']" :aria-label="labels.mainMenu">
      <nav class="ui vertical large fluid inverted menu" role="navigation" :aria-label="labels.mainMenu">
        <div :class="[{collapsed: !exploreExpanded}, 'collaspable item']">
          <header class="header" @click="exploreExpanded = true" tabindex="0" @focus="exploreExpanded = true">
            <translate translate-context="*/*/*/Verb">Explore</translate>
            <i class="angle right icon" v-if="!exploreExpanded"></i>
          </header>
          <div class="menu">
            <router-link class="item" :exact="true" :to="{name: 'library.index'}"><i class="music icon"></i><translate translate-context="Sidebar/Navigation/List item.Link/Verb">Browse</translate></router-link>
            <router-link class="item" :to="{name: 'library.albums.browse'}"><i class="compact disc icon"></i><translate translate-context="*/*/*">Albums</translate></router-link>
            <router-link class="item" :to="{name: 'library.artists.browse'}"><i class="user icon"></i><translate translate-context="*/*/*">Artists</translate></router-link>
            <router-link class="item" :to="{name: 'library.playlists.browse'}"><i class="list icon"></i><translate translate-context="*/*/*">Playlists</translate></router-link>
            <router-link class="item" :to="{name: 'library.radios.browse'}"><i class="feed icon"></i><translate translate-context="*/*/*">Radios</translate></router-link>
          </div>
        </div>
        <div :class="[{collapsed: !myLibraryExpanded}, 'collaspable item']" v-if="$store.state.auth.authenticated">
          <header class="header" @click="myLibraryExpanded = true" tabindex="0" @focus="myLibraryExpanded = true">
            <translate translate-context="*/*/*/Noun">My Library</translate>
            <i class="angle right icon" v-if="!myLibraryExpanded"></i>
          </header>
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
          <header class="header">
            <translate translate-context="Footer/About/List item.Link">More</translate>
          </header>
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
        "library.index": 'exploreExpanded',
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

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
@import "../style/vendor/media";

$sidebar-color: #2D2F33;

.sidebar {
  background: $sidebar-color;
  z-index: 1;
  @include media(">desktop") {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding-bottom: 4em;
  }
  > nav {
    flex-grow: 1;
    overflow-y: auto;
  }
  @include media(">desktop") {
    .menu .item.collapse-button-wrapper {
      padding: 0;
    }
    .collapse.button {
      display: none !important;
    }
  }
  @include media("<=desktop") {
    position: static !important;
    width: 100% !important;
    &.collapsed {
      .player-wrapper,
      .search,
      .signup.segment,
      nav.secondary {
        display: none;
      }
    }
  }

  > div {
    margin: 0;
    background-color: $sidebar-color;
  }
  .menu.vertical {
    background: $sidebar-color;
  }
}

.ui.vertical.menu {
  .item .item {
    font-size: 1em;
    > i.icon {
      float: none;
      margin: 0 0.5em 0 0;
    }
    &:not(.active) {
      // color: rgba(255, 255, 255, 0.75);
    }
  }
  .item.active {
    border-right: 5px solid #F2711C;
    border-radius: 0 !important;
    background-color: rgba(255, 255, 255, 0.15) !important;
  }
  .item.collapsed {
    &:not(:focus) > .menu {
      display: none;
    }
    .header {
      margin-bottom: 0;
    }
  }
  .collaspable.item .header {
    cursor: pointer;
  }
}
.ui.secondary.menu {
  margin-left: 0;
  margin-right: 0;
}
.tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  justify-content: space-between;
  @include media("<=desktop") {
    max-height: 500px;
  }
}
.ui.tab.active {
  display: flex;
}
.tab[data-tab="queue"] {
  flex-direction: column;
  tr {
    cursor: pointer;
  }
  td:nth-child(2) {
    width: 55px;
  }
}
.item .header .angle.icon {
  float: right;
  margin: 0;
}
.tab[data-tab="library"] {
  flex-direction: column;
  flex: 1 1 auto;
  > .menu {
    flex: 1;
    flex-grow: 1;
  }
  > .player-wrapper {
    width: 100%;
  }
}
.sidebar .segment {
  margin: 0;
  border-radius: 0;
}

.ui.menu .item.inline.admin-dropdown.dropdown > .menu {
  left: 0;
  right: auto;
}
.ui.segment.header-wrapper {
  padding: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 4em;
  nav {
    > .item, > .menu > .item > .item {
      &:hover {
        background-color: transparent;
      }
    }
  }
}

nav.top.title-menu {
  flex-grow: 1;
  .item {
    font-size: 1.5em;
  }
}

.logo {
  cursor: pointer;
  display: inline-block;
  margin: 0px;
}

.collapsed .search-wrapper {
  @include media("<desktop") {
    padding: 0;
  }
}
.ui.search {
  display: flex;
}
.ui.message.black {
  background: $sidebar-color;
}

.ui.mini.image {
  width: 100%;
}
nav.top {
  align-items: self-end;
  padding: 0.5em 0;
  > .item, > .right.menu > .item {
    // color: rgba(255, 255, 255, 0.9) !important;
    font-size: 1.2em;
    &:hover, > .dropdown > .icon {
      // color: rgba(255, 255, 255, 0.9) !important;
    }
    > .label, > .dropdown > .label {
      font-size: 0.5em;
      right: 1.7em;
      bottom: -0.5em;
      z-index: 0 !important;
    }
  }
}
.ui.user-dropdown > .text > .label {
  margin-right: 0;
}
.logo-wrapper {
  display: inline-block;
  margin: 0 auto;
  @include media("<desktop") {
    margin: 0;
  }
  img {
    height: 1em;
    display: inline-block;
    margin: 0 auto;
  }
  @include media(">tablet") {
    img {
      height: 1.5em;
    }
  }
}
</style>

<style lang="scss">
aside.ui.sidebar {
  overflow-y: visible !important;
  .ui.search .input {
    flex: 1;
    .prompt {
      border-radius: 0;
    }
  }
  .ui.search .results {
    vertical-align: middle;
  }
  .ui.search .name {
    vertical-align: middle;
  }
}
.ui.tiny.avatar.image {
  position: relative;
  top: -0.5em;
  width: 3em;
}

:not(.active) button.title {
  outline-color: white;
}
</style>
