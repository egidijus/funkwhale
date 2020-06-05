<template>
  <main class="main pusher page-home" v-title="labels.title">
    <section :class="['ui', 'head', {'with-background': banner}, 'vertical', 'center', 'aligned', 'stripe', 'segment']" :style="headerStyle">
      <div class="segment-content">
        <h1 class="ui center aligned large header">
          <span
            v-translate="{podName: podName}"
            translate-context="Content/Home/Header"
            :translate-params="{podName: podName}">
            Welcome to %{ podName }!
          </span>
          <div v-if="shortDescription" class="sub header">
            {{ shortDescription }}
          </div>
        </h1>
      </div>
    </section>
    <section class="ui vertical stripe segment">
      <div class="ui stackable grid">
        <div class="ten wide column">
          <h3 class="header">
            <translate translate-context="Content/Home/Header">About this Funkwhale pod</translate>
          </h3>
          <div class="ui raised segment" id="pod">
            <div class="ui stackable grid">
              <div class="eight wide column">
                <p v-if="!truncatedDescription">
                  <translate translate-context="Content/Home/Paragraph">No description available.</translate>
                </p>
                <template v-if="truncatedDescription || rules">
                  <div v-if="truncatedDescription" v-html="truncatedDescription"></div>
                  <div v-if="truncatedDescription" class="ui hidden divider"></div>
                  <div class="ui relaxed list">
                    <div class="item" v-if="truncatedDescription">
                      <i class="arrow right icon"></i>
                      <div class="content">
                        <router-link class="ui link" :to="{name: 'about'}">
                          <translate translate-context="Content/Home/Link">Learn more</translate>
                        </router-link>
                      </div>
                    </div>
                    <div class="item" v-if="rules">
                      <i class="book open icon"></i>
                      <div class="content">
                        <router-link class="ui link" v-if="rules" :to="{name: 'about', hash: '#rules'}">
                          <translate translate-context="Content/Home/Link">Server rules</translate>
                        </router-link>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
              <div class="eight wide column">
                <template v-if="stats">
                  <h3 class="sub header">
                    <translate translate-context="Content/Home/Header">Statistics</translate>
                  </h3>
                  <p>
                    <i class="user icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.users.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.users" translate-plural="%{ count } active users">%{ count } active user</translate>
                  </p>
                  <p>
                    <i class="music icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: parseInt(stats.hours).toLocaleString($store.state.ui.momentLocale)}" :translate-n="parseInt(stats.hours)" translate-plural="%{ count } hours of music">%{ count } hour of music</translate>
                  </p>

                </template>
                <template v-if="contactEmail">
                  <h3 class="sub header">
                    <translate translate-context="Content/Home/Header/Name">Contact</translate>
                  </h3>
                  <i class="at icon"></i>
                  <a :href="`mailto:${contactEmail}`">{{ contactEmail }}</a>
                </template>

              </div>
            </div>
          </div>
        </div>

        <div class="six wide column">
          <img class="ui image" src="../assets/network.png" />
        </div>
      </div>
      <div class="ui hidden divider"></div>
      <div class="ui hidden divider"></div>
      <div class="ui stackable grid">
        <div class="four wide column">
          <h3 class="header">
            <translate translate-context="Footer/*/Title/Short">About Funkwhale</translate>
          </h3>
          <p v-translate translate-context="Content/Home/Paragraph">This pod runs Funkwhale, a community-driven project that lets you listen and share music and audio within a decentralized, open network.</p>
          <p v-translate translate-context="Content/Home/Paragraph">Funkwhale is free and developped by a friendly community of volunteers.</p>
          <a target="_blank" rel="noopener" href="https://funkwhale.audio">
            <i class="external alternate icon"></i>
            <translate translate-context="Content/Home/Link">Visit funkwhale.audio</translate>
          </a>
        </div>
        <div class="four wide column">
          <h3 class="header">
            <translate translate-context="Head/Login/Title">Log In</translate>
          </h3>
          <login-form button-classes="basic success" :show-signup="false"></login-form>
          <div class="ui hidden clearing divider"></div>
        </div>
        <div class="four wide column">
          <h3 class="header">
            <translate translate-context="*/Signup/Title">Sign up</translate>
          </h3>
          <template v-if="openRegistrations">
            <p>
              <translate translate-context="Content/Home/Paragraph">Sign up now to keep a track of your favorites, create playlists, discover new content and much more!</translate>
            </p>
            <p v-if="defaultUploadQuota">
              <translate translate-context="Content/Home/Paragraph" :translate-params="{quota: humanSize(defaultUploadQuota * 1000 * 1000)}">Users on this pod also get %{ quota } of free storage to upload their own content!</translate>
            </p>
            <signup-form button-classes="basic success" :show-login="false"></signup-form>
          </template>
          <div v-else>
            <p translate-context="Content/Home/Paragraph">Registrations are closed on this pod. You can signup on another pod using the link below.</p>
            <a target="_blank" rel="noopener" href="https://funkwhale.audio/#get-started">
              <i class="external alternate icon"></i>
              <translate translate-context="Content/Home/Link">Find another pod</translate>
            </a>
          </div>
        </div>

        <div class="four wide column">
          <h3 class="header">
            <translate translate-context="Content/Home/Header">Useful links</translate>
          </h3>
          <div class="ui relaxed list">
            <div class="item">
              <i class="headphones icon"></i>
              <div class="content">
                <router-link v-if="anonymousCanListen" class="header" to="/library">
                  <translate translate-context="Content/Home/Link">Browse public content</translate>
                </router-link>
                <div class="description">
                  <translate translate-context="Content/Home/Link">Listen to public albums and playlists shared on this pod</translate>
                </div>
              </div>
            </div>
            <div class="item">
              <i class="mobile alternate icon"></i>
              <div class="content">
                <a class="header" href="https://funkwhale.audio/apps" target="_blank" rel="noopener">
                  <translate translate-context="Content/Home/Link">Mobile apps</translate>
                </a>
                <div class="description">
                  <translate translate-context="Content/Home/Link">Use Funkwhale on other devices with our apps</translate>
                </div>
              </div>
            </div>
            <div class="item">
              <i class="book icon"></i>
              <div class="content">
                <a class="header" href="https://docs.funkwhale.audio/users/index.html" target="_blank" rel="noopener">
                  <translate translate-context="Content/Home/Link">User guides</translate>
                </a>
                <div class="description">
                  <translate translate-context="Content/Home/Link">Discover everything you need to know about Funkwhale and its features</translate>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    <section v-if="anonymousCanListen" class="ui vertical stripe segment">
      <album-widget :filters="{playable: true, ordering: '-creation_date'}" :limit="10">
        <template slot="title"><translate translate-context="Content/Home/Title">Recently added albums</translate></template>
        <router-link to="/library">
          <translate translate-context="Content/Home/Link">View more…</translate>
          <div class="ui hidden divider"></div>
        </router-link>
      </album-widget>
      <div class="ui hidden section divider"></div>
      <h3 class="ui header" >
        <translate translate-context="*/*/*">New channels</translate>
      </h3>
      <channels-widget :show-modification-date="true" :limit="10" :filters="{ordering: '-creation_date', external: 'false'}"></channels-widget>

    </section>
  </main>
</template>

<script>
import $ from 'jquery'
import _ from '@/lodash'
import {mapState} from 'vuex'
import showdown from 'showdown'
import AlbumWidget from "@/components/audio/album/Widget"
import ChannelsWidget from "@/components/audio/ChannelsWidget"
import LoginForm from "@/components/auth/LoginForm"
import SignupForm from "@/components/auth/SignupForm"
import {humanSize } from '@/filters'

export default {
  components: {
    AlbumWidget,
    ChannelsWidget,
    LoginForm,
    SignupForm,
  },
  data () {
    return {
      markdown: new showdown.Converter(),
      excerptLength: 2, // html nodes,
      humanSize
    }
  },
  computed: {
    ...mapState({
      nodeinfo: state => state.instance.nodeinfo,
    }),
    labels() {
      return {
        title: this.$pgettext('Head/Home/Title', "Welcome")
      }
    },
    podName() {
      return _.get(this.nodeinfo, 'metadata.nodeName') || "Funkwhale"
    },
    banner () {
      return _.get(this.nodeinfo, 'metadata.banner')
    },
    shortDescription () {
      return _.get(this.nodeinfo, 'metadata.shortDescription')
    },
    longDescription () {
      return _.get(this.nodeinfo, 'metadata.longDescription')
    },
    rules () {
      return _.get(this.nodeinfo, 'metadata.rules')
    },
    truncatedDescription () {
      if (!this.longDescription) {
        return
      }
      let doc = this.markdown.makeHtml(this.longDescription)
      let nodes = $.parseHTML(doc)
      let excerptParts = []
      let handled = 0
      nodes.forEach((n) => {
        let content = n.innerHTML || n.nodeValue
        if (handled < this.excerptLength && content.trim()) {
          excerptParts.push(n)
          handled += 1
        }
      })
      return excerptParts.map((p) => { return p.outerHTML }).join('')
    },
    stats () {
      let data = {
        users: _.get(this.nodeinfo, 'usage.users.activeMonth', null),
        hours: _.get(this.nodeinfo, 'metadata.library.music.hours', null),
      }
      if (data.users === null || data.artists === null) {
        return
      }
      return data
    },
    contactEmail () {
      return _.get(this.nodeinfo, 'metadata.contactEmail')
    },
    defaultUploadQuota () {
      return _.get(this.nodeinfo, 'metadata.defaultUploadQuota')
    },
    anonymousCanListen () {
      return _.get(this.nodeinfo, 'metadata.library.anonymousCanListen')
    },
    openRegistrations () {
      return _.get(this.nodeinfo, 'openRegistrations')
    },
    headerStyle() {
      if (!this.banner) {
        return ""
      }
      return (
        "background-image: url(" +
        this.$store.getters["instance/absoluteUrl"](this.banner) +
        ")"
      )
    },
  },
  watch: {
    '$store.state.auth.authenticated': {
      handler (v) {
        if (v) {
          console.log('Authenticated, redirecting to /library…')
          this.$router.push('/library')
        }
      },
      immediate: true
    }
  }

}
</script>
