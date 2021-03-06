<template>
  <main v-title="labels.playlists">
    <section class="ui vertical stripe segment">
      <h2 class="ui header"><translate translate-context="Content/Playlist/Title">Browsing playlists</translate></h2>
      <template v-if="$store.state.auth.authenticated">
        <button
          @click="$store.commit('playlists/chooseTrack', null)"
          class="ui success button"><translate translate-context="Content/Playlist/Button.Label/Verb">Manage your playlists</translate></button>
        <div class="ui hidden divider"></div>
      </template>
      <form :class="['ui', {'loading': isLoading}, 'form']" @submit.prevent="updateQueryString();fetchData()">
        <div class="fields">
          <div class="field">
            <label for="playlists-search"><translate translate-context="Content/Search/Input.Label/Noun">Search</translate></label>
            <div class="ui action input">
              <input id="playlists-search" stype="text" name="search" v-model="query" :placeholder="labels.searchPlaceholder"/>
              <button class="ui icon button" type="submit" :aria-label="$pgettext('Content/Search/Input.Label/Noun', 'Search')">
                <i class="search icon"></i>
              </button>
            </div>
          </div>
          <div class="field">
            <label for="playlists-ordering"><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
            <select id="playlists-ordering" class="ui dropdown" v-model="ordering">
              <option v-for="option in orderingOptions" :value="option[0]">
                {{ sharedLabels.filters[option[1]] }}
              </option>
            </select>
          </div>
          <div class="field">
            <label for="playlists-ordering-direction"><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
            <select id="playlists-ordering-direction" class="ui dropdown" v-model="orderingDirection">
              <option value="+"><translate translate-context="Content/Search/Dropdown">Ascending</translate></option>
              <option value="-"><translate translate-context="Content/Search/Dropdown">Descending</translate></option>
            </select>
          </div>
          <div class="field">
            <label for="playlists-results"><translate translate-context="Content/Search/Dropdown.Label/Noun">Results per page</translate></label>
            <select id="playlists-results" class="ui dropdown" v-model="paginateBy">
              <option :value="parseInt(12)">12</option>
              <option :value="parseInt(25)">25</option>
              <option :value="parseInt(50)">50</option>
            </select>
          </div>
        </div>
      </form>
      <div class="ui hidden divider"></div>
      <playlist-card-list v-if="result && result.results.length > 0" :playlists="result.results"></playlist-card-list>
      <div v-else-if="result && !result.results.length > 0" class="ui placeholder segment sixteen wide column" style="text-align: center; display: flex; align-items: center">
        <div class="ui icon header">
          <i class="list icon"></i>
          <translate translate-context="Content/Playlists/Placeholder">
            No results matching your query
          </translate>
        </div>
        <button
        v-if="$store.state.auth.authenticated"
        @click="$store.commit('playlists/chooseTrack', null)"
        class="ui success button labeled icon">
        <i class="list icon"></i>
        <translate translate-context="Content/*/Verb">
          Create a playlist
          </translate>
        </button>
      </div>
      <div class="ui center aligned basic segment">
        <pagination
          v-if="result && result.results.length > 0"
          @page-changed="selectPage"
          :current="page"
          :paginate-by="paginateBy"
          :total="result.count"
          ></pagination>
      </div>
    </section>
  </main>
</template>

<script>
import axios from "axios"
import _ from "@/lodash"
import $ from "jquery"

import OrderingMixin from "@/components/mixins/Ordering"
import PaginationMixin from "@/components/mixins/Pagination"
import TranslationsMixin from "@/components/mixins/Translations"
import PlaylistCardList from "@/components/playlists/CardList"
import Pagination from "@/components/Pagination"

const FETCH_URL = "playlists/"

export default {
  mixins: [OrderingMixin, PaginationMixin, TranslationsMixin],
  props: {
    defaultQuery: { type: String, required: false, default: "" },
    scope: { type: String, required: false, default: "all" },
  },
  components: {
    PlaylistCardList,
    Pagination
  },
  data() {
    return {
      isLoading: true,
      result: null,
      page: parseInt(this.defaultPage),
      query: this.defaultQuery,
      orderingOptions: [
        ["creation_date", "creation_date"],
        ["modification_date", "modification_date"],
        ["name", "name"]
      ]
    }
  },
  created() {
    this.fetchData()
  },
  mounted() {
    $(".ui.dropdown").dropdown()
  },
  computed: {
    labels() {
      let playlists = this.$pgettext('*/*/*', 'Playlists')
      let searchPlaceholder = this.$pgettext('Content/Playlist/Placeholder/Call to action', 'Enter playlist name…')
      return {
        playlists,
        searchPlaceholder
      }
    }
  },
  methods: {
    updateQueryString: function() {
      history.pushState(
        {},
        null,
        this.$route.path + '?' + new URLSearchParams(
          {
          query: this.query,
          page: this.page,
          paginateBy: this.paginateBy,
          ordering: this.getOrderingAsString()
        }).toString()
      )
    },
    fetchData: function() {
      var self = this
      this.isLoading = true
      let url = FETCH_URL
      let params = {
        scope: this.scope,
        page: this.page,
        page_size: this.paginateBy,
        q: this.query,
        ordering: this.getOrderingAsString(),
        playable: true
      }
      axios.get(url, { params: params }).then(response => {
        self.result = response.data
        self.isLoading = false
      })
    },
    selectPage: function(page) {
      this.page = page
    }
  },
  watch: {
    page() {
      this.updateQueryString()
      this.fetchData()
    },
  }
}
</script>
