<template>
  <div class="ui fluid user-request card">
    <div class="content">
      <div class="header">
        <router-link :to="{name: 'manage.moderation.requests.detail', params: {id: obj.uuid}}">
          <translate translate-context="Content/Moderation/Card/Short" :translate-params="{id: obj.uuid.substring(0, 8)}">Request %{ id }</translate>
        </router-link>
        <collapse-link class="right floated" v-model="isCollapsed"></collapse-link>
      </div>
      <div class="content">
        <div class="ui hidden divider"></div>
        <div class="ui stackable two column grid">
          <div class="column">
            <table class="ui very basic unstackable table">
              <tbody>
                <tr>
                  <td>
                    <translate translate-context="Content/Moderation/*">Submitted by</translate>
                  </td>
                  <td>
                    <actor-link :admin="true" :actor="obj.submitter" />
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*/Noun">Creation date</translate>
                  </td>
                  <td>
                    <human-date :date="obj.creation_date" :icon="true"></human-date>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="column">
            <table class="ui very basic unstackable table">
              <tbody>
                <tr>
                  <td>
                    <translate translate-context="*/*/*">Status</translate>
                  </td>
                  <td>
                    <template v-if="obj.status === 'pending'">
                      <i class="warning hourglass icon"></i>
                      <translate translate-context="Content/Library/*/Short">Pending</translate>
                    </template>
                    <template v-else-if="obj.status === 'refused'">
                      <i class="danger x icon"></i>
                      <translate translate-context="Content/*/*/Short">Refused</translate>
                    </template>
                    <template v-else-if="obj.status === 'approved'">
                      <i class="success check icon"></i>
                      <translate translate-context="Content/*/*/Short">Approved</translate>
                    </template>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/Moderation/*">Assigned to</translate>
                  </td>
                  <td>
                    <div v-if="obj.assigned_to">
                      <actor-link :admin="true" :actor="obj.assigned_to" />
                    </div>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*/Noun">Resolution date</translate>
                  </td>
                  <td>
                    <human-date v-if="obj.handled_date" :date="obj.handled_date" :icon="true"></human-date>
                    <translate v-else translate-context="*/*/*">N/A</translate>
                  </td>
                </tr>
                <tr>
                  <td>
                    <translate translate-context="Content/*/*/Noun">Internal notes</translate>
                  </td>
                  <td>
                    <i class="comment icon"></i>
                    {{ obj.notes.length }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    <div class="main content" v-if="!isCollapsed">
      <div class="ui stackable two column grid">
        <div class="column">
          <h3>
            <translate translate-context="*/*/Field.Label/Noun">Message</translate>
          </h3>
          <p>
            <translate translate-context="Content/Moderation/Paragraph">This user wants to sign-up on your pod.</translate>
          </p>
          <template v-if="obj.metadata">
            <div class="ui hidden divider"></div>
            <div v-for="k in Object.keys(obj.metadata)" :key="k">
              <h4>{{ k }}</h4>
              <p v-if="obj.metadata[k] && obj.metadata[k].length">{{ obj.metadata[k] }}</p>
              <translate v-else translate-context="*/*/*">N/A</translate>
              <div class="ui hidden divider"></div>
            </div>
          </template>
        </div>
        <aside class="column">
          <div v-if="obj.status != 'approved'">
            <h3>
              <translate translate-context="Content/*/*/Noun">Actions</translate>
            </h3>
            <div class="ui labelled icon basic buttons">
              <button
                v-if="obj.status === 'pending' || obj.status === 'refused'"
                @click="approve(true)"
                :class="['ui', {loading: isLoading}, 'button']">
                <i class="success check icon"></i>&nbsp;
                <translate translate-context="Content/*/Button.Label/Verb">Approve</translate>
              </button>
              <button
                v-if="obj.status === 'pending'"
                @click="approve(false)"
                :class="['ui', {loading: isLoading}, 'button']">
                <i class="danger x icon"></i>&nbsp;
                <translate translate-context="Content/*/Button.Label">Refuse</translate>
              </button>
            </div>
          </div>
          <h3>
            <translate translate-context="Content/*/*/Noun">Internal notes</translate>
          </h3>
          <notes-thread @deleted="handleRemovedNote($event)" :notes="obj.notes" />
          <note-form @created="obj.notes.push($event)" :target="{type: 'request', uuid: obj.uuid}" />
        </aside>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import NoteForm from '@/components/manage/moderation/NoteForm'
import NotesThread from '@/components/manage/moderation/NotesThread'
import {setUpdate} from '@/utils'
import showdown from 'showdown'


export default {
  props: {
    obj: {required: true},
  },
  components: {
    NoteForm,
    NotesThread,
  },
  data () {
    return {
      markdown: new showdown.Converter(),
      isLoading: false,
      isCollapsed: false,
    }
  },
  methods: {
    approve (v) {
      let url = `manage/moderation/requests/${this.obj.uuid}/`
      let self = this
      let newStatus = v ? 'approved' : 'refused'
      this.isLoading = true
      axios.patch(url, {status: newStatus}).then((response) => {
        self.$emit('handled', newStatus)
        self.isLoading = false
        self.obj.status = newStatus
        if (v) {
          self.isCollapsed = true
        }
        self.$store.commit('ui/incrementNotifications', {count: -1, type: 'pendingReviewRequests'})
      }, error => {
        self.isLoading = false
      })
    },
    handleRemovedNote (uuid) {
      this.obj.notes = this.obj.notes.filter((note) => {
        return note.uuid != uuid
      })
    },
  }
}
</script>
