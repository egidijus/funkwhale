<template>
  <section class="ui vertical aligned stripe segment">
    <div v-if="isLoading" :class="['ui', {'active': isLoading}, 'inverted', 'dimmer']">
      <div class="ui text loader"><translate translate-context="Content/Library/Paragraph">Loading Libraries…</translate></div>
    </div>
    <div v-else class="ui text container">
      <h1 class="ui header"><translate translate-context="Content/Library/Title">My libraries</translate></h1>

      <p v-if="libraries.length == 0">
        <translate translate-context="Content/Library/Paragraph">Looks like you don't have a library, it's time to create one.</translate>
      </p>
      <a :aria-expanded="!hiddenForm" @click="hiddenForm = !hiddenForm" href="">
        <i class="plus icon" v-if="hiddenForm" />
        <i class="minus icon" v-else />
        <translate translate-context="Content/Library/Link/Verb">Create a new library</translate>
      </a>
      <library-form :library="null" v-if="!hiddenForm" @created="libraryCreated" />
      <div class="ui hidden divider"></div>
      <quota />
      <div class="ui hidden divider"></div>
      <div v-if="libraries.length > 0" class="ui two column grid">
        <div v-for="library in libraries" :key="library.uuid" class="column">
          <library-card :library="library" />
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import axios from "axios"
import LibraryForm from "./Form"
import LibraryCard from "./Card"
import Quota from "./Quota"

export default {
  data() {
    return {
      isLoading: false,
      hiddenForm: true,
      libraries: []
    }
  },
  created() {
    this.fetch()
  },
  components: {
    LibraryForm,
    LibraryCard,
    Quota
  },
  methods: {
    fetch() {
      this.isLoading = true
      let self = this
      axios.get("libraries/", {params: {scope: 'me'}}).then(response => {
        self.isLoading = false
        self.libraries = response.data.results
        if (self.libraries.length === 0) {
          self.hiddenForm = false
        }
      })
    },
    libraryCreated(library) {
      this.$router.push({name: 'library.detail', params: {id: library.uuid}})
    }
  }
}
</script>
