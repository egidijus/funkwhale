<template>
  <main>
    <div v-if="isLoading" class="ui vertical segment" v-title="labels.title">
      <div :class="['ui', 'centered', 'active', 'inline', 'loader']"></div>
    </div>
    <section v-if="!isLoading && radio" class="ui head vertical center aligned stripe segment" v-title="radio.name">
      <div class="segment-content">
        <h2 class="ui center aligned icon header">
          <i class="circular inverted feed primary icon"></i>
          <div class="content">
            {{ radio.name }}
            <div class="sub header">
              Radio containing {{ totalTracks }} tracks,
              by <username :username="radio.user.username"></username>
            </div>
          </div>
        </h2>
        <div class="ui hidden divider"></div>
        <radio-button type="custom" :custom-radio-id="radio.id"></radio-button>
        <template v-if="$store.state.auth.username === radio.user.username">
          <router-link class="ui icon labeled button" :to="{name: 'library.radios.edit', params: {id: radio.id}}" exact>
            <i class="pencil icon"></i>
            Edit…
          </router-link>
          <dangerous-button class="ui labeled danger icon button" :action="deleteRadio">
            <i class="trash icon"></i> Delete
            <p slot="modal-header" v-translate="{radio: radio.name}"  translate-context="Popup/Radio/Title" :translate-params="{radio: radio.name}">Do you want to delete the radio "%{ radio }"?</p>
            <p slot="modal-content"><translate translate-context="Popup/Radio/Paragraph">This will completely delete this radio and cannot be undone.</translate></p>
            <p slot="modal-confirm"><translate translate-context="Popup/Radio/Button.Label/Verb">Delete radio</translate></p>
          </dangerous-button>
        </template>
      </div>
    </section>
    <section v-if="totalTracks > 0" class="ui vertical stripe segment">
      <h2><translate translate-context="*/*/*">Tracks</translate></h2>
      <track-table :tracks="tracks"></track-table>
      <div class="ui center aligned basic segment">
        <pagination
          v-if="totalTracks > 25"
          @page-changed="selectPage"
          :current="page"
          :paginate-by="25"
          :total="totalTracks"
          ></pagination>
      </div>
    </section>
    <div v-else-if="!isLoading && !totalTracks > 0" class="ui placeholder segment">
      <div class="ui icon header">
        <i class="rss icon"></i>
        <translate
        translate-context="Content/Radios/Placeholder"
        >No tracks have been added to this radio yet</translate>
      </div>
      <router-link
      v-if="$store.state.auth.username === radio.user.username"
      class="ui success icon labeled button"
      :to="{name: 'library.radios.edit', params: {id: radio.id}}" exact>
      <i class="pencil icon"></i>
        Edit…
      </router-link>
    </div>
  </main>
</template>

<script>
import axios from "axios"
import TrackTable from "@/components/audio/track/Table"
import RadioButton from "@/components/radios/Button"
import Pagination from "@/components/Pagination"

export default {
  props: {
    id: { required: true }
  },
  components: {
    TrackTable,
    RadioButton,
    Pagination
  },
  data: function() {
    return {
      isLoading: false,
      radio: null,
      tracks: [],
      totalTracks: 0,
      page: 1
    }
  },
  created: function() {
    this.fetch()
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/Radio/Title', "Radio")
      }
    }
  },
  methods: {
    selectPage: function(page) {
      this.page = page
    },
    fetch: function() {
      let self = this
      self.isLoading = true
      let url = "radios/radios/" + this.id + "/"
      axios.get(url).then(response => {
        self.radio = response.data
        axios
          .get(url + "tracks/", { params: { page: this.page } })
          .then(response => {
            this.totalTracks = response.data.count
            this.tracks = response.data.results
          })
          .then(() => {
            self.isLoading = false
          })
      })
    },
    deleteRadio() {
      let self = this
      let url = "radios/radios/" + this.id + "/"
      axios.delete(url).then(response => {
        self.$router.push({
          path: "/library"
        })
      })
    }
  },
  watch: {
    page: function() {
      this.fetch()
    }
  }
}
</script>
