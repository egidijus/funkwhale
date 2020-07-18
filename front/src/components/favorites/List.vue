<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical center aligned stripe segment">
      <div :class="['ui', {'active': isLoading}, 'inverted', 'dimmer']">
        <div class="ui text loader">
          <translate translate-context="Content/Favorites/Message">Loading your favorites…</translate>
        </div>
      </div>
      <h2 v-if="results" class="ui center aligned icon header">
        <i class="circular inverted heart pink icon"></i>
        <translate
          translate-plural="%{ count } favorites"
          :translate-n="$store.state.favorites.count"
          :translate-params="{count: results.count}"
          translate-context="Content/Favorites/Title">
	%{ count } favorite
        </translate>
      </h2>
      <radio-button v-if="hasFavorites" type="favorites"></radio-button>
    </section>
    <section v-if="hasFavorites" class="ui vertical stripe segment">
      <div :class="['ui', {'loading': isLoading}, 'form']">
        <div class="fields">
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate></label>
            <select class="ui dropdown" v-model="ordering">
              <option v-for="option in orderingOptions" :value="option[0]">
                {{ sharedLabels.filters[option[1]] }}
              </option>
            </select>
          </div>
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Order</translate></label>
            <select class="ui dropdown" v-model="orderingDirection">
              <option value="+"><translate translate-context="Content/Search/Dropdown">Ascending</translate></option>
              <option value="-"><translate translate-context="Content/Search/Dropdown">Descending</translate></option>
            </select>
          </div>
          <div class="field">
            <label><translate translate-context="Content/Search/Dropdown.Label/Noun">Results per page</translate></label>
            <select class="ui dropdown" v-model="paginateBy">
              <option :value="parseInt(12)">12</option>
              <option :value="parseInt(25)">25</option>
              <option :value="parseInt(50)">50</option>
            </select>
          </div>
        </div>
      </div>
      <track-table v-if="results" :tracks="results.results"></track-table>
      <div class="ui center aligned basic segment">
        <pagination
          v-if="results && results.count > paginateBy"
          @page-changed="selectPage"
          :current="page"
          :paginate-by="paginateBy"
          :total="results.count"
          ></pagination>
      </div>
    </section>
    <div v-else class="ui placeholder segment">
      <div class="ui icon header">
        <i class="broken heart icon"></i>
        <translate
          translate-context="Content/Home/Placeholder"
        >No tracks have been added to your favorites yet</translate>
      </div>
      <router-link :to="'/library'" class="ui success labeled icon button">
      <i class="headphones icon"></i>
        <translate translate-context="Content/*/Verb">Browse the library</translate>
      </router-link>
    </div>
  </main>
</template>

<script>
import axios from "axios"
import $ from "jquery"
import logger from "@/logging"
import TrackTable from "@/components/audio/track/Table"
import RadioButton from "@/components/radios/Button"
import Pagination from "@/components/Pagination"
import OrderingMixin from "@/components/mixins/Ordering"
import PaginationMixin from "@/components/mixins/Pagination"
import TranslationsMixin from "@/components/mixins/Translations"
import {checkRedirectToLogin} from '@/utils'
const FAVORITES_URL = "tracks/"

export default {
  mixins: [OrderingMixin, PaginationMixin, TranslationsMixin],
  components: {
    TrackTable,
    RadioButton,
    Pagination
  },
  data() {
    return {
      results: null,
      isLoading: false,
      nextLink: null,
      previousLink: null,
      page: parseInt(this.defaultPage),
      orderingOptions: [
        ["creation_date", "creation_date"],
        ["title", "track_title"],
        ["album__title", "album_title"],
        ["artist__name", "artist_name"]
      ]
    }
  },
  created() {
    checkRedirectToLogin(this.$store, this.$router)
    this.fetchFavorites(FAVORITES_URL)

  },
  mounted() {
    $(".ui.dropdown").dropdown()
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/Favorites/Title', 'Your Favorites')
      }
    },
    hasFavorites () {
      return this.$store.state.favorites.count > 0
    },
  },
  methods: {
    updateQueryString: function() {
      this.$router.replace({
        query: {
          page: this.page,
          paginateBy: this.paginateBy,
          ordering: this.getOrderingAsString()
        }
      })
      this.fetchFavorites(FAVORITES_URL)
    },
    fetchFavorites(url) {
      var self = this
      this.isLoading = true
      let params = {
        favorites: "true",
        page: this.page,
        page_size: this.paginateBy,
        ordering: this.getOrderingAsString()
      }
      logger.default.time("Loading user favorites")
      axios.get(url, { params: params }).then(response => {
        self.results = response.data
        self.nextLink = response.data.next
        self.previousLink = response.data.previous
        self.results.results.forEach(track => {
          self.$store.commit("favorites/track", { id: track.id, value: true })
        })
        logger.default.timeEnd("Loading user favorites")
        self.isLoading = false
      })
    },
    selectPage: function(page) {
      this.page = page
    }
  },
  watch: {
    page: function() {
      this.updateQueryString()
    },
    paginateBy: function() {
      this.updateQueryString()
    },
    orderingDirection: function() {
      this.updateQueryString()
    },
    ordering: function() {
      this.updateQueryString()
    }
  }
}
</script>
