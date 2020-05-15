<template>
  <div class="ui feed">
    <div class="event" v-for="note in notes" :key="note.uuid">
      <div class="label">
        <i class="comment outline icon"></i>
      </div>
      <div class="content">
        <div class="summary">
          <actor-link :admin="true" :actor="note.author"></actor-link>
          <div class="date">
            <human-date :date="note.creation_date"></human-date>
          </div>
        </div>
        <div class="extra text">
          <expandable-div :content="note.summary">
            <div v-html="markdown.makeHtml(note.summary)"></div>
          </expandable-div>
        </div>
        <div class="meta">
          <dangerous-button
            :class="['ui', {loading: isLoading}, 'basic borderless mini button']"
            @confirm="remove(note)">
            <i class="trash icon"></i>
            <translate translate-context="*/*/*/Verb">Delete</translate>
            <p slot="modal-header"><translate translate-context="Popup/Moderation/Title">Delete this note?</translate></p>
            <div slot="modal-content">
              <p><translate translate-context="Content/Moderation/Paragraph">The note will be removed. This action is irreversible.</translate></p>
            </div>
            <p slot="modal-confirm"><translate translate-context="*/*/*/Verb">Delete</translate></p>
          </dangerous-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import showdown from 'showdown'

export default {
  props: {
    notes: {required: true},
  },
  data () {
      return {
      markdown: new showdown.Converter(),
      isLoading: false,
    }
  },
  methods: {
    remove (obj) {
      let self = this
      this.isLoading = true
      axios.delete(`manage/moderation/notes/${obj.uuid}/`).then((response) => {
        self.$emit('deleted', obj.uuid)
        self.isLoading = false
      }, error => {
        self.isLoading = false
      })
    },
  }
}
</script>
