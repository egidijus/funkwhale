<template>
  <button class="ui button" @click.prevent="show = !show">
    <i class="shield icon"></i>&nbsp;
    <slot>
      <translate translate-context="Content/Moderation/Button.Label">Moderation rules…</translate>
    </slot>
    <modal :show.sync="show" @show="fetchData">
      <h4 class="header">
        <translate :translate-params="{obj: target}" translate-context="Popup/Moderation/Title/Verb">Manage moderation rules for %{ obj }</translate>
      </h4>
      <div class="content">
        <div class="description">
          <div v-if="isLoading" class="ui active loader"></div>
          <instance-policy-card v-else-if="obj && !showForm" :object="obj" @update="showForm = true">
            <header class="ui header">
              <h3>
                <translate translate-context="Content/Moderation/Card.Title">This entity is subject to specific moderation rules</translate>
              </h3>
            </header>
            </instance-policy-card>
            <instance-policy-form
              v-else
              @cancel="showForm = false"
              @save="showForm = false; result = {count: 1, results: [$event]}"
              @delete="result = {count: 0, results: []}; showForm = false"
              :object="obj"
              :type="type"
              :target="target" />
        </div>
        <div class="ui hidden divider"></div>
        <div class="ui hidden divider"></div>
      </div>
      <div class="actions">
        <button class="ui deny button">
          <translate translate-context="*/*/Button.Label/Verb">Close</translate>
        </button>
      </div>
    </modal>

  </button>
</template>

<script>
import axios from 'axios'
import InstancePolicyForm from "@/components/manage/moderation/InstancePolicyForm"
import InstancePolicyCard from "@/components/manage/moderation/InstancePolicyCard"
import Modal from '@/components/semantic/Modal'

export default {
  props: {
    target: {required: true},
    type: {required: true},
  },
  components: {
    InstancePolicyForm,
    InstancePolicyCard,
    Modal,
  },
  data () {
    return {
      show: false,
      isLoading: false,
      errors: [],
      showForm: false,
      result: null,
    }
  },
  computed: {
    obj () {
      if (!this.result) {
        return null
      }
      return this.result.results[0]
    }
  },
  methods: {
    fetchData () {
      let params = {}
      if (this.type === 'domain') {
        params.target_domain = this.target
      }
      if (this.type === 'actor') {
        let parts = this.target.split('@')
        params.target_account_username = parts[0]
        params.target_account_domain = parts[1]
      }
      let self = this
      self.isLoading = true
      axios.get('/manage/moderation/instance-policies/', {params: params}).then((response) => {
        self.result = response.data
        self.isLoading = false
      }, error => {
        self.isLoading = false
        self.errors = error.backendErrors
      })
    }
  }
}
</script>
