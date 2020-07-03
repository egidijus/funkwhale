<template>
  <div class="ui fluid card">
    <div class="content">
      <h4 class="header">
        <router-link :to="detailUrl">
          <translate translate-context="Content/Library/Card/Short" :translate-params="{id: obj.uuid.substring(0, 8)}">Modification %{ id }</translate>
        </router-link>
      </h4>
      <div class="meta">
        <router-link
          v-if="obj.target && obj.target.type === 'track'"
          :to="{name: 'library.tracks.detail', params: {id: obj.target.id }}">
          <i class="music icon"></i>
          <translate translate-context="Content/Library/Card/Short" :translate-params="{id: obj.target.id, name: obj.target.repr}">Track #%{ id } - %{ name }</translate>
        </router-link>
        <br>
        <human-date :date="obj.creation_date" :icon="true"></human-date>

        <span class="right floated">
          <span v-if="obj.is_approved && obj.is_applied">
            <i class="success check icon"></i>
            <translate translate-context="Content/Library/Card/Short">Approved and applied</translate>
          </span>
          <span v-else-if="obj.is_approved">
            <i class="success check icon"></i>
            <translate translate-context="Content/*/*/Short">Approved</translate>
          </span>
          <span v-else-if="obj.is_approved === null">
            <i class="warning hourglass icon"></i>
            <translate translate-context="Content/Admin/*/Noun">Pending review</translate>
          </span>
          <span v-else-if="obj.is_approved === false">
            <i class="danger x icon"></i>
            <translate translate-context="Content/Library/*/Short">Rejected</translate>
          </span>
        </span>
      </div>
    </div>
    <div v-if="obj.summary" class="content">
      {{ obj.summary }}
    </div>
    <div class="content">
      <table v-if="obj.type === 'update'" class="ui celled very basic fixed stacking table">
        <thead>
          <tr>
            <th><translate translate-context="Content/Library/Card.Table.Header/Short">Field</translate></th>
            <th><translate translate-context="Content/Library/Card.Table.Header/Short">Old value</translate></th>
            <th><translate translate-context="Content/Library/Card.Table.Header/Short">New value</translate></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="field in updatedFields" :key="field.id">
            <td>{{ field.id }}</td>

            <td v-if="field.diff">
              <template v-if="field.config.type === 'attachment' && field.oldRepr">
                <img class="ui image" :src="$store.getters['instance/absoluteUrl'](`api/v1/attachments/${field.oldRepr}/proxy?next=medium_square_crop`)" />
              </template>
              <template v-else>
                <span v-if="!part.added" v-for="part in field.diff" :class="['diff', {removed: part.removed}]">
                  {{ part.value }}
                </span>
              </template>
            </td>
            <td v-else>
              <translate translate-context="*/*/*">N/A</translate>
            </td>

            <td v-if="field.diff" :title="field.newRepr">
              <template v-if="field.config.type === 'attachment' && field.newRepr">
                <img class="ui image" :src="$store.getters['instance/absoluteUrl'](`api/v1/attachments/${field.newRepr}/proxy?next=medium_square_crop`)" />
              </template>
              <template v-else>
                <span v-if="!part.removed" v-for="part in field.diff" :class="['diff', {added: part.added}]">
                  {{ part.value }}
                </span>
              </template>
            </td>
            <td v-else :title="field.newRepr">
              <template v-if="field.config.type === 'attachment' && field.newRepr">
                <img class="ui image" :src="$store.getters['instance/absoluteUrl'](`api/v1/attachments/${field.newRepr}/proxy?next=medium_square_crop`)" />
              </template>
              <template v-else>
                {{ field.newRepr }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="obj.created_by" class="extra content">
      <actor-link :actor="obj.created_by" />
    </div>
    <div v-if="canDelete || canApprove" class="ui bottom attached buttons">
      <button
        v-if="canApprove && obj.is_approved !== true"
        @click="approve(true)"
        :class="['ui', {loading: isLoading}, 'success', 'basic', 'button']">
        <translate translate-context="Content/*/Button.Label/Verb">Approve</translate>
      </button>
      <button
        v-if="canApprove && obj.is_approved === null"
        @click="approve(false)"
        :class="['ui', {loading: isLoading}, 'warning', 'basic', 'button']">
        <translate translate-context="Content/Library/Button.Label">Reject</translate>
      </button>
      <dangerous-button
        v-if="canDelete"
        :class="['ui', {loading: isLoading}, 'basic danger button']"
        :action="remove">
        <translate translate-context="*/*/*/Verb">Delete</translate>
        <p slot="modal-header"><translate translate-context="Popup/Library/Title">Delete this suggestion?</translate></p>
        <div slot="modal-content">
          <p><translate translate-context="Popup/Library/Paragraph">The suggestion will be completely removed, this action is irreversible.</translate></p>
        </div>
        <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
      </dangerous-button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { diffWordsWithSpace } from 'diff'

import edits from '@/edits'

function castValue (value) {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

export default {
  props: {
    obj: {required: true},
    currentState: {required: false}
  },
  data () {
    return {
      isLoading: false
    }
  },
  computed: {
    configs: edits.getConfigs,
    canApprove: edits.getCanApprove,
    canDelete: edits.getCanDelete,
    previousState () {
      if (this.obj.is_applied) {
        // mutation was applied, we use the previous state that is stored
        // on the mutation itself
        return this.obj.previous_state
      }
      // mutation is not applied yet, so we use the current state that was
      // passed to the component, if any
      return this.currentState
    },
    detailUrl () {
      if (!this.obj.target) {
        return ''
      }
      let namespace
      let id = this.obj.target.id
      if (this.obj.target.type === 'track') {
        namespace = 'library.tracks.edit.detail'
      }
      if (this.obj.target.type === 'album') {
        namespace = 'library.albums.edit.detail'
      }
      if (this.obj.target.type === 'artist') {
        namespace = 'library.artists.edit.detail'
      }
      return this.$router.resolve({name: namespace, params: {id, editId: this.obj.uuid}}).href
    },

    updatedFields () {
      if (!this.obj.target) {
        return []
      }
      let payload = this.obj.payload
      let previousState = this.previousState
      let fields = Object.keys(payload)
      let self = this
      return fields.map((f) => {
        let fieldConfig = edits.getFieldConfig(self.configs, this.obj.target.type, f)
        let dummyRepr = (v) => { return v }
        let getValueRepr = fieldConfig.getValueRepr || dummyRepr
        let d = {
          id: f,
          config: fieldConfig
        }
        if (previousState && previousState[f]) {
          d.old = previousState[f]
          d.oldRepr = castValue(getValueRepr(d.old.value))
        }
        d.new = payload[f]
        d.newRepr = castValue(getValueRepr(d.new))
        if (d.old) {
          // we compute the diffs between the old and new values
          d.diff = diffWordsWithSpace(d.oldRepr, d.newRepr)
        }
        return d
      })
    }
  },
  methods: {
    remove () {
      let self = this
      this.isLoading = true
      axios.delete(`mutations/${this.obj.uuid}/`).then((response) => {
        self.$emit('deleted')
        self.isLoading = false
      }, error => {
        self.isLoading = false
      })
    },
    approve (approved) {
      let url
      if (approved) {
        url = `mutations/${this.obj.uuid}/approve/`
      } else {
        url = `mutations/${this.obj.uuid}/reject/`
      }
      let self = this
      this.isLoading = true
      axios.post(url).then((response) => {
        self.$emit('approved', approved)
        self.isLoading = false
        self.$store.commit('ui/incrementNotifications', {count: -1, type: 'pendingReviewEdits'})
      }, error => {
        self.isLoading = false
      })
    },
  }
}
</script>
