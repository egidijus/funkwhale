<template>
  <form @submit.stop.prevent :class="['ui', {loading: isLoading}, 'form']">
    <div v-if="errors.length > 0" role="alert" class="ui negative message">
      <div class="header"><translate translate-context="Content/*/Error message.Title">Error while creating</translate></div>
      <ul class="list">
        <li v-for="error in errors">{{ error }}</li>
      </ul>
    </div>
    <div class="ui required field">
      <label for="album-title">
        <translate translate-context="*/*/*/Noun">Title</translate>
      </label>
      <input type="text" v-model="values.title">
    </div>
  </form>
</template>
<script>
import axios from 'axios'

export default {
  props: {
    channel: {type: Object, required: true},
  },
  components: {},
  data () {
    return {
      errors: [],
      isLoading: false,
      values: {
        title: "",
      },
    }
  },
  computed: {
    submittable () {
      return this.values.title.length > 0
    }
  },
  methods: {

    submit () {
      let self = this
      self.isLoading = true
      self.errors = []
      let payload = {
        ...this.values,
        artist: this.channel.artist.id,
      }
      return axios.post('albums/', payload).then(
        response => {
          self.isLoading = false
          self.$emit("created")
        },
        error => {
          self.errors = error.backendErrors
          self.isLoading = false
        }
      )
    }
  },
  watch: {
    submittable (v) {
      this.$emit("submittable", v)
    },
    isLoading (v) {
      this.$emit("loading", v)
    }
  }
}
</script>
