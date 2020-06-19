<template>
  <main v-title="labels.domains">
    <section class="ui vertical stripe segment">
      <h2 class="ui left floated header"><translate translate-context="*/Moderation/*/Noun">Domains</translate></h2>
      <form class="ui right floated form" @submit.prevent="createDomain">
        <div v-if="errors && errors.length > 0" role="alert" class="ui negative message">
          <div class="header"><translate translate-context="Content/Moderation/Message.Title">Error while creating domain</translate></div>
          <ul class="list">
            <li v-for="error in errors">{{ error }}</li>
          </ul>
        </div>
        <div class="inline fields">
          <div class="field">
            <label for="domain"><translate translate-context="Content/Moderation/Form.Label/Verb">Add a domain</translate></label>
            <input type="text" name="domain" id="domain" v-model="domainName">
          </div>
          <div class="field" v-if="allowListEnabled">
            <input type="checkbox" name="allowed" id="allowed" v-model="domainAllowed">
            <label for="allowed"><translate translate-context="Content/Moderation/Action/Verb">Add to allow-list</translate></label>
          </div>
          <div class="field">
            <button :class="['ui', {'loading': isCreating}, 'success', 'button']" type="submit" :disabled="isCreating">
              <label for="domain"><translate translate-context="Content/Moderation/Button/Verb">Add</translate></label>
            </button>
          </div>
        </div>
      </form>
      <div class="ui clearing hidden divider"></div>
      <domains-table :allow-list-enabled="allowListEnabled"></domains-table>
    </section>
  </main>
</template>

<script>
import axios from 'axios'

import DomainsTable from "@/components/manage/moderation/DomainsTable"
export default {
  props: ['allowListEnabled'],
  components: {
    DomainsTable
  },
  data () {
    return {
      domainName: '',
      domainAllowed: this.allowListEnabled ? true : null,
      isCreating: false,
      errors: []
    }
  },
  computed: {
    labels() {
      return {
        domains: this.$pgettext('*/Moderation/*/Noun', "Domains")
      }
    }
  },
  methods: {
    createDomain () {
      let self = this
      this.isCreating = true
      this.errors = []
      axios.post('manage/federation/domains/', {name: this.domainName, allowed: this.domainAllowed}).then((response) => {
        this.isCreating = false
        this.$router.push({
          name: "manage.moderation.domains.detail",
          params: {'id': response.data.name}
        })
      }, (error) => {
        self.isCreating = false
        self.errors = error.backendErrors
      })
    }
  }
}
</script>
