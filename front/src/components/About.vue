<template>
  <main class="main pusher page-about">
    <section :class="['ui', 'head', {'with-background': banner}, 'vertical', 'center', 'aligned', 'stripe', 'segment']" :style="headerStyle">
      <div class="segment-content">
        <h1 class="ui center aligned large header">
          <span
            v-translate="{podName: podName}"
            translate-context="Content/Home/Header"
            :translate-params="{podName: podName}">
            About %{ podName }!
          </span>
          <div v-if="shortDescription" class="sub header">
            {{ shortDescription }}
          </div>
        </h1>
      </div>
    </section>
    <section class="ui vertical stripe segment">
      <div class="ui container">
        <div class="ui mobile reversed stackable grid">
          <div class="ten wide column">
            <div class="ui text container">
              <h3 class="ui header" id="description">
                <translate translate-context="Content/About/Header">About this pod</translate>
              </h3>
              <div v-html="markdown.makeHtml(longDescription)" v-if="longDescription"></div>
              <p v-else>
                <translate translate-context="Content/Home/Paragraph">No description available.</translate>
              </p>
              <h3 class="ui header" id="rules">
                <translate translate-context="Content/About/Header">Rules</translate>
              </h3>
              <div v-html="markdown.makeHtml(rules)" v-if="rules"></div>
              <p v-else>
                <translate translate-context="Content/Home/Paragraph">No rules available.</translate>
              </p>
              <h3 class="ui header" id="terms">
                <translate translate-context="Content/About/Header">Terms and privacy policy</translate>
              </h3>
              <div v-html="markdown.makeHtml(terms)" v-if="terms"></div>
              <p v-else>
                <translate translate-context="Content/Home/Paragraph">No terms available.</translate>
              </p>
            </div>
          </div>
          <div class="six wide column">
            <div class="ui raised segment">
              <h3 class="ui header">
                <translate translate-context="Content/About/Header">Contents</translate>
              </h3>
              <div class="ui list">
                <div class="ui item">
                  <a href="#description">
                    <translate translate-context="Content/About/Header">About this pod</translate>
                  </a>
                </div>
                <div class="ui item">
                  <a href="#rules">
                    <translate translate-context="Content/About/Header">Rules</translate>
                  </a>
                </div>
                <div class="ui item">
                  <a href="#terms">
                    <translate translate-context="Content/About/Header">Terms and privacy policy</translate>
                  </a>
                </div>
              </div>
              <template v-if="contactEmail">
                <h3 class="header">
                  <translate translate-context="Content/Home/Header/Name">Contact</translate>
                </h3>
                <a :href="`mailto:${contactEmail}`">{{ contactEmail }}</a>
              </template>
              <h3 class="header">
                <translate translate-context="Content/About/Header/Name">Pod configuration</translate>
              </h3>
              <table class="ui very basic table">
                <tbody>
                  <tr v-if="version">
                    <td>
                      <translate translate-context="*/*/*">Funkwhale version</translate>
                    </td>
                    <td>
                      {{ version }}
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Registrations</translate>
                    </td>
                    <td v-if="openRegistrations">
                      <i class="check icon"></i>
                      <translate translate-context="*/*/*/State of registrations">Open</translate>
                    </td>
                    <td v-else>
                      <i class="x icon"></i>
                      <translate translate-context="*/*/*/State of registrations">Closed</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Upload quota</translate>
                    </td>
                    <td v-if="defaultUploadQuota">
                      {{ defaultUploadQuota * 1000 * 1000 | humanSize }}
                    </td>
                    <td v-else>
                      <translate translate-context="*/*/*">N/A</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Federation</translate>
                    </td>
                    <td v-if="federationEnabled">
                      <i class="check icon"></i>
                      <translate translate-context="*/*/*/State of feature">Enabled</translate>
                    </td>
                    <td v-else>
                      <i class="x icon"></i>
                      <translate translate-context="*/*/*/State of feature">Disabled</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Anonymous access</translate>
                    </td>
                    <td v-if="anonymousCanListen">
                      <i class="check icon"></i>
                      <translate translate-context="*/*/*/State of feature">Enabled</translate>
                    </td>
                    <td v-else>
                      <i class="x icon"></i>
                      <translate translate-context="*/*/*/State of feature">Disabled</translate>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <translate translate-context="*/*/*">Allow-list</translate>
                    </td>
                    <td v-if="allowListEnabled">
                      <i class="check icon"></i>
                      <translate translate-context="*/*/*/State of feature">Enabled</translate>
                    </td>
                    <td v-else>
                      <i class="x icon"></i>
                      <translate translate-context="*/*/*/State of feature">Disabled</translate>
                    </td>
                  </tr>
                  <tr v-if="allowListDomains">
                    <td>
                      <translate translate-context="*/*/*">Allowed domains</translate>
                    </td>
                    <td>
                      <translate :translate-n="allowListDomains.length"  translate-plural="%{ count } allowed domains" :translate-params="{count: allowListDomains.length}" translate-context="*/*/*">%{ count } allowed domains</translate>
                      <br>
                      <a @click.prevent="showAllowedDomains = !showAllowedDomains">
                        <translate v-if="showAllowedDomains" key="1" translate-context="*/*/*/Verb">Hide</translate>
                        <translate v-else key="2" translate-context="*/*/*/Verb">Show</translate>
                      </a>
                      <ul class="ui list" v-if="showAllowedDomains">
                        <li v-for="domain in allowListDomains" :key="domain">
                          <a :href="`https://${domain}`" target="_blank" rel="noopener">{{ domain }}</a>
                        </li>
                      </ul>
                    </td>
                  </tr>
                </tbody>
              </table>

              <template v-if="stats">
                <h3 class="header">
                  <translate translate-context="Content/Home/Header">Statistics</translate>
                </h3>
                <p>
                  <i class="user really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.users.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.users" translate-plural="%{ count } active users">%{ count } active user</translate>
                </p>
                <p>
                  <i class="music really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: parseInt(stats.hours).toLocaleString($store.state.ui.momentLocale)}" :translate-n="parseInt(stats.hours)" translate-plural="%{ count } hours of music">%{ count } hour of music</translate>
                </p>
                <p v-if="stats.artists">
                  <i class="users really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.artists.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.artists" translate-plural="%{ count } artists">%{ count } artists</translate>
                </p>
                <p v-if="stats.albums">
                  <i class="headphones really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.albums.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.albums" translate-plural="%{ count } albums">%{ count } albums</translate>
                </p>
                <p v-if="stats.tracks">
                  <i class="file really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.tracks.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.tracks" translate-plural="%{ count } tracks">%{ count } tracks</translate>
                </p>
                <p v-if="stats.listenings">
                  <i class="play really discrete icon"></i><translate translate-context="Content/Home/Stat" :translate-params="{count: stats.listenings.toLocaleString($store.state.ui.momentLocale) }" :translate-n="stats.listenings" translate-plural="%{ count } listenings">%{ count } listenings</translate>
                </p>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script>
import { mapState } from "vuex"
import _ from '@/lodash'
import showdown from 'showdown'

export default {
  data () {
    return {
      markdown: new showdown.Converter(),
      showAllowedDomains: false,
    }
  },
  computed: {

  ...mapState({
      nodeinfo: state => state.instance.nodeinfo,
    }),
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
    terms () {
      return _.get(this.nodeinfo, 'metadata.terms')
    },
    stats () {
      let data = {
        users: _.get(this.nodeinfo, 'usage.users.activeMonth', null),
        hours: _.get(this.nodeinfo, 'metadata.library.music.hours', null),
        artists: _.get(this.nodeinfo, 'metadata.library.artists.total', null),
        albums: _.get(this.nodeinfo, 'metadata.library.albums.total', null),
        tracks: _.get(this.nodeinfo, 'metadata.library.tracks.total', null),
        listenings: _.get(this.nodeinfo, 'metadata.usage.listenings.total', null),
      }
      if (data.users === null || data.artists === null) {
        return
      }
      return data
    },
    contactEmail () {
      return _.get(this.nodeinfo, 'metadata.contactEmail')
    },
    anonymousCanListen () {
      return _.get(this.nodeinfo, 'metadata.library.anonymousCanListen')
    },
    allowListEnabled () {
      return _.get(this.nodeinfo, 'metadata.allowList.enabled')
    },
    allowListDomains () {
      return _.get(this.nodeinfo, 'metadata.allowList.domains')
    },
    version () {
      return _.get(this.nodeinfo, 'software.version')
    },
    openRegistrations () {
      return _.get(this.nodeinfo, 'openRegistrations')
    },
    defaultUploadQuota () {
      return _.get(this.nodeinfo, 'metadata.defaultUploadQuota')
    },
    federationEnabled () {
      return _.get(this.nodeinfo, 'metadata.library.federationEnabled')
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
  }
}
</script>
