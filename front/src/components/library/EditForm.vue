<template>
  <div v-if="submittedMutation">
    <div class="ui positive message">
      <div class="header"><translate translate-context="Content/Library/Paragraph">Your edit was successfully submitted.</translate></div>
    </div>
    <edit-card :obj="submittedMutation" :current-state="currentState" />
    <button class="ui button" @click.prevent="submittedMutation = null">
      <translate translate-context="Content/Library/Button.Label">
        Submit another edit
      </translate>
    </button>
  </div>
  <div v-else>

    <edit-list :filters="editListFilters" :url="mutationsUrl" :obj="object" :currentState="currentState">
      <div slot="title">
        <template v-if="showPendingReview">
          <translate translate-context="Content/Library/Paragraph">
            Recent edits awaiting review
          </translate>
          <button class="ui tiny basic right floated button" @click.prevent="showPendingReview = false">
            <translate translate-context="Content/Library/Button.Label">
              Show all edits
            </translate>
          </button>
        </template>
        <template v-else>
          <translate translate-context="Content/Library/Paragraph">
            Recent edits
          </translate>
          <button class="ui tiny basic right floated button" @click.prevent="showPendingReview = true">
            <translate translate-context="Content/Library/Button.Label">
              Restrict to unreviewed edits
            </translate>
          </button>
        </template>
      </div>
      <empty-state slot="empty-state">
        <translate translate-context="Content/Library/Paragraph">
          Suggest a change using the form below.
        </translate>
      </empty-state>
    </edit-list>
    <form class="ui form" @submit.prevent="submit()">
      <div class="ui hidden divider"></div>
      <div v-if="errors.length > 0" role="alert" class="ui negative message">
        <div class="header"><translate translate-context="Content/Library/Error message.Title">Error while submitting edit</translate></div>
        <ul class="list">
          <li v-for="error in errors">{{ error }}</li>
        </ul>
      </div>
      <div v-if="!canEdit" class="ui message">
        <translate translate-context="Content/Library/Paragraph">
          You don't have the permission to edit this object, but you can suggest changes. Once submitted, suggestions will be reviewed before approval.
        </translate>
      </div>
      <div v-if="values" v-for="fieldConfig in config.fields" :key="fieldConfig.id" class="ui field">
        <template v-if="fieldConfig.type === 'text'">
          <label :for="fieldConfig.id">{{ fieldConfig.label }}</label>
          <input :type="fieldConfig.inputType || 'text'" v-model="values[fieldConfig.id]" :required="fieldConfig.required" :name="fieldConfig.id" :id="fieldConfig.id">
        </template>
        <template v-else-if="fieldConfig.type === 'license'">
          <label :for="fieldConfig.id">{{ fieldConfig.label }}</label>

          <select
            ref="license"
            v-model="values[fieldConfig.id]"
            :required="fieldConfig.required"
            :id="fieldConfig.id"
            class="ui fluid search dropdown">
              <option :value="null"><translate translate-context="*/*/*">N/A</translate></option>
              <option v-for="license in licenses" :key="license.code" :value="license.code">{{ license.name}}</option>
          </select>
          <button class="ui tiny basic left floated button" form="noop" @click.prevent="values[fieldConfig.id] = null">
            <i class="x icon"></i>
            <translate translate-context="Content/Library/Button.Label">Clear</translate>
          </button>

        </template>
        <template v-else-if="fieldConfig.type === 'content'">
          <label :for="fieldConfig.id">{{ fieldConfig.label }}</label>
          <content-form v-model="values[fieldConfig.id].text" :field-id="fieldConfig.id" :rows="3"></content-form>
        </template>
        <template v-else-if="fieldConfig.type === 'attachment'">
          <attachment-input
            v-model="values[fieldConfig.id]"
            :initial-value="initialValues[fieldConfig.id]"
            :required="fieldConfig.required"
            :name="fieldConfig.id"
            :id="fieldConfig.id"
            @delete="values[fieldConfig.id] = initialValues[fieldConfig.id]">
            <span slot="label">{{ fieldConfig.label }}</span>
          </attachment-input>

        </template>
        <template v-else-if="fieldConfig.type === 'tags'">
          <label :for="fieldConfig.id">{{ fieldConfig.label }}</label>
          <tags-selector
            ref="tags"
            v-model="values[fieldConfig.id]"
            :id="fieldConfig.id"
            required="fieldConfig.required"></tags-selector>
          <button class="ui tiny basic left floated button" form="noop" @click.prevent="values[fieldConfig.id] = []">
            <i class="x icon"></i>
            <translate translate-context="Content/Library/Button.Label">Clear</translate>
          </button>
        </template>
        <div v-if="!lodash.isEqual(values[fieldConfig.id], initialValues[fieldConfig.id])">
          <button class="ui tiny basic right floated reset button" form="noop" @click.prevent="values[fieldConfig.id] = lodash.clone(initialValues[fieldConfig.id])">
            <i class="undo icon"></i>
            <translate translate-context="Content/Library/Button.Label">Reset to initial value</translate>
          </button>
        </div>
      </div>
      <div class="field">
        <label for="summary"><translate translate-context="*/*/*">Summary (optional)</translate></label>
        <textarea name="change-summary" v-model="summary" id="change-summary" rows="3" :placeholder="labels.summaryPlaceholder"></textarea>
      </div>
      <router-link
        class="ui left floated button"
        v-if="objectType === 'track'"
        :to="{name: 'library.tracks.detail', params: {id: object.id }}"
      >
        <translate translate-context="*/*/Button.Label/Verb">Cancel</translate>
      </router-link>
      <button :class="['ui', {'loading': isLoading}, 'right', 'floated', 'green', 'button']" type="submit" :disabled="isLoading || !mutationPayload">
        <translate v-if="canEdit" key="1" translate-context="Content/Library/Button.Label/Verb">Submit and apply edit</translate>
        <translate v-else key="2" translate-context="Content/Library/Button.Label/Verb">Submit suggestion</translate>
      </button>
    </form>
  </div>
</template>

<script>
import $ from 'jquery'
import _ from '@/lodash'
import axios from "axios"
import AttachmentInput from '@/components/common/AttachmentInput'
import EditList from '@/components/library/EditList'
import EditCard from '@/components/library/EditCard'
import TagsSelector from '@/components/library/TagsSelector'
import edits from '@/edits'

import lodash from '@/lodash'

export default {
  props: ["objectType", "object", "licenses"],
  components: {
    EditList,
    EditCard,
    TagsSelector,
    AttachmentInput
  },
  data() {
    return {
      isLoading: false,
      errors: [],
      values: {},
      initialValues: {},
      summary: '',
      submittedMutation: null,
      showPendingReview: true,
      lodash,
    }
  },
  created () {
    this.setValues()
  },
  mounted() {
    $(".ui.dropdown").dropdown({fullTextSearch: true})
  },
  computed: {
    configs: edits.getConfigs,
    config: edits.getConfig,
    currentState: edits.getCurrentState,
    canEdit: edits.getCanEdit,
    labels () {
      return {
        summaryPlaceholder: this.$pgettext('*/*/Placeholder', 'A short summary describing your changes.'),
      }
    },
    mutationsUrl () {
      if (this.objectType === 'track') {
        return `tracks/${this.object.id}/mutations/`
      }
      if (this.objectType === 'album') {
        return `albums/${this.object.id}/mutations/`
      }
      if (this.objectType === 'artist') {
        return `artists/${this.object.id}/mutations/`
      }
    },
    mutationPayload () {
      let self = this
      let changedFields = this.config.fields.filter(f => {
        return !lodash.isEqual(self.values[f.id], self.initialValues[f.id])
      })
      if (changedFields.length === 0) {
        return null
      }
      let payload = {
        type: 'update',
        payload: {},
        summary: this.summary,
      }
      changedFields.forEach((f) => {
        payload.payload[f.id] = self.values[f.id]
      })
      return payload
    },
    editListFilters () {
      if (this.showPendingReview) {
        return {is_approved: 'null'}
      } else {
        return {}
      }
    },
  },

  methods: {
    setValues () {
      let self = this
      this.config.fields.forEach(f => {
        self.$set(self.values, f.id, lodash.clone(f.getValue(self.object)))
        self.$set(self.initialValues, f.id, lodash.clone(self.values[f.id]))
      })
    },
    submit() {
      let self = this
      self.isLoading = true
      self.errors = []
      let payload = _.clone(this.mutationPayload || {})
      if (this.canEdit) {
        payload.is_approved = true
      }
      return axios.post(this.mutationsUrl, payload).then(
        response => {
          self.isLoading = false
          self.submittedMutation = response.data
        },
        error => {
          self.errors = error.backendErrors
          self.isLoading = false
        }
      )
    }
  },
  watch: {
    'values.license' (newValue) {
      if (newValue === null) {
        $(this.$refs.license).dropdown('clear')
      } else {
        $(this.$refs.license).dropdown('set selected', newValue)
      }
    }
  }
}
</script>
<style>
.reset.button {
  margin-top: 0.5em;
}
</style>
