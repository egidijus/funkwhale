<template>
  <div class="table-wrapper component-action-table">
    <table class="ui compact very basic unstackable table">
      <thead>
        <tr>
          <th colspan="1000">
            <div v-if="refreshable" class="right floated">
              <span v-if="needsRefresh">
                <translate translate-context="Content/*/Button.Help text.Paragraph">Content has been updated, click refresh to see up-to-date content</translate>
              </span>
              <button
                @click="$emit('refresh')"
                class="ui basic icon button"
                :title="labels.refresh"
                :aria-label="labels.refresh">
                <i class="refresh icon"></i>
              </button>
            </div>

            <div class="ui small left floated form" v-if="actionUrl && actions.length > 0">
              <div class="ui inline fields">
                <div class="field">
                  <label for="actions-select"><translate translate-context="Content/*/*/Noun">Actions</translate></label>
                  <select id="actions-select" class="ui dropdown" v-model="currentActionName">
                    <option v-for="action in actions" :value="action.name">
                      {{ action.label }}
                    </option>
                  </select>
                </div>
                <div class="field">
                  <dangerous-button
                    v-if="selectAll || currentAction.isDangerous" :class="['ui', {disabled: checked.length === 0}, {'loading': actionLoading}, 'button']"
                    :confirm-color="currentAction.confirmColor || 'success'"
                    @confirm="launchAction" :aria-label="labels.performAction">
                    <translate translate-context="Content/*/Button.Label/Short, Verb">Go</translate>
                    <p slot="modal-header">
                      <translate translate-context="Modal/*/Title"
                        key="1"
                        :translate-n="affectedObjectsCount"
                        :translate-params="{count: affectedObjectsCount, action: currentActionName}"
                        translate-plural="Do you want to launch %{ action } on %{ count } elements?">
                        Do you want to launch %{ action } on %{ count } element?
                      </translate>
                    </p>
                    <p slot="modal-content">
                      <template v-if="currentAction.confirmationMessage">{{ currentAction.confirmationMessage }}</template>
                      <translate v-else translate-context="Modal/*/Paragraph">This may affect a lot of elements or have irreversible consequences, please double check this is really what you want.</translate>
                    </p>
                    <div :aria-label="labels.performAction" slot="modal-confirm"><translate translate-context="Modal/*/Button.Label/Short, Verb">Launch</translate></div>
                  </dangerous-button>
                  <div
                    v-else
                    @click="launchAction"
                    :disabled="checked.length === 0"
                    :aria-label="labels.performAction"
                    :class="['ui', {disabled: checked.length === 0}, {'loading': actionLoading}, 'button']">
                    <translate translate-context="Content/*/Button.Label/Short, Verb">Go</translate></div>
                </div>
                <div class="count field">
                  <translate translate-context="Content/*/Paragraph"
                    tag="span"
                    v-if="selectAll"
                    key="1"
                    :translate-n="objectsData.count"
                    :translate-params="{count: objectsData.count, total: objectsData.count}"
                    translate-plural="All %{ count } elements selected">
                    All %{ count } element selected
                  </translate>
                  <translate translate-context="Content/*/Paragraph"
                    tag="span"
                    v-else
                    key="2"
                    :translate-n="checked.length"
                    :translate-params="{count: checked.length, total: objectsData.count}"
                    translate-plural="%{ count } on %{ total } selected">
                    %{ count } on %{ total } selected
                  </translate>
                  <template v-if="currentAction.allowAll && checkable.length > 0 && checkable.length === checked.length">
                    <a @click="selectAll = true" v-if="!selectAll">
                      <translate translate-context="Content/*/Link/Verb"
                        key="3"
                        :translate-n="objectsData.count"
                        :translate-params="{total: objectsData.count}"
                        translate-plural="Select all %{ total } elements">
                        Select all %{ total } elements
                      </translate>
                    </a>
                    <a @click="selectAll = false" v-else>
                      <translate translate-context="Content/*/Link/Verb" key="4">Select only current page</translate>
                    </a>
                  </template>
                </div>
              </div>
              <div v-if="actionErrors.length > 0" role="alert" class="ui negative message">
                <h4 class="header"><translate translate-context="Content/*/Error message/Header">Error while applying action</translate></h4>
                <ul class="list">
                  <li v-for="error in actionErrors">{{ error }}</li>
                </ul>
              </div>
              <div v-if="actionResult" class="ui positive message">
                <p>
                  <translate translate-context="Content/*/Paragraph"
                    :translate-n="actionResult.updated"
                    :translate-params="{count: actionResult.updated, action: actionResult.action}"
                    translate-plural="Action %{ action } was launched successfully on %{ count } elements">
                    Action %{ action } was launched successfully on %{ count } element
                  </translate>
                </p>

                <slot name="action-success-footer" :result="actionResult">
                </slot>
              </div>
            </div>
          </th>
        </tr>
        <tr>
          <th v-if="actions.length > 0">
            <div class="ui checkbox">
              <input
                type="checkbox"
                @change="toggleCheckAll"
                :aria-label="labels.selectAllItems"
                :disabled="checkable.length === 0"
                :checked="checkable.length > 0 && checked.length === checkable.length">
            </div>
          </th>
          <slot name="header-cells"></slot>
        </tr>
      </thead>
      <tbody v-if="objectsData.count > 0">
        <tr v-for="(obj, index) in objects">
          <td v-if="actions.length > 0" class="collapsing">
            <input
              type="checkbox"
              :aria-label="labels.selectItem"
              :disabled="checkable.indexOf(getId(obj)) === -1"
              @click="toggleCheck($event, getId(obj), index)"
              :checked="checked.indexOf(getId(obj)) > -1">
          </td>
          <slot name="row-cells" :obj="obj"></slot>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script>
import axios from 'axios'

export default {
  props: {
    actionUrl: {type: String, required: false, default: null},
    idField: {type: String, required: false, default: 'id'},
    refreshable: {type: Boolean, required: false, default: false},
    needsRefresh: {type: Boolean, required: false, default: false},
    objectsData: {type: Object, required: true},
    actions: {type: Array, required: true, default: () => { return [] }},
    filters: {type: Object, required: false, default: () => { return {} }},
    customObjects: {type: Array, required: false, default: () => { return [] }},
  },
  components: {},
  data () {
    let d = {
      checked: [],
      actionLoading: false,
      actionResult: null,
      actionErrors: [],
      currentActionName: null,
      selectAll: false,
      lastCheckedIndex: -1
    }
    if (this.actions.length > 0) {
      d.currentActionName = this.actions[0].name
    }
    return d
  },
  methods: {
    toggleCheckAll () {
      this.lastCheckedIndex = -1
      if (this.checked.length === this.checkable.length) {
        // we uncheck
        this.checked = []
      } else {
        this.checked = this.checkable.map(i => { return i })
      }
    },
    toggleCheck (event, id, index) {
      let self = this
      let affectedIds = [id]
      let newValue = null
      if (this.checked.indexOf(id) > -1) {
        // we uncheck
        this.selectAll = false
        newValue = false
      } else {
        newValue = true
      }
      if (event.shiftKey && this.lastCheckedIndex > -1) {
        // we also add inbetween ids to the list of affected ids
        let idxs = [index, this.lastCheckedIndex]
        idxs.sort((a, b) => a - b)
        let objs = this.objectsData.results.slice(idxs[0], idxs[1] + 1)
        affectedIds = affectedIds.concat(objs.map((o) => { return o.id }))
      }
      affectedIds.forEach((i) => {
        let checked = self.checked.indexOf(i) > -1
        if (newValue && !checked && self.checkable.indexOf(i) > -1) {
          return self.checked.push(i)
        }
        if (!newValue && checked) {
          self.checked.splice(self.checked.indexOf(i), 1)
        }
      })
      this.lastCheckedIndex = index
    },
    launchAction () {
      let self = this
      self.actionLoading = true
      self.result = null
      self.actionErrors = []
      let payload = {
        action: this.currentActionName,
        filters: this.filters
      }
      if (this.selectAll) {
        payload.objects = 'all'
      } else {
        payload.objects = this.checked
      }
      axios.post(this.actionUrl, payload).then((response) => {
        self.actionResult = response.data
        self.actionLoading = false
        self.$emit('action-launched', response.data)
      }, error => {
        self.actionLoading = false
        self.actionErrors = error.backendErrors
      })
    },
    getId (obj) {
      return obj[this.idField]
    }
  },
  computed: {
    currentAction () {
      let self = this
      return this.actions.filter((a) => {
        return a.name === self.currentActionName
      })[0]
    },
    checkable () {
      let self = this
      if (!this.currentAction) {
        return []
      }
      let objs = this.objectsData.results
      let filter = this.currentAction.filterCheckable
      if (filter) {
        objs = objs.filter((o) => {
          return filter(o)
        })
      }
      return objs.map((o) => { return self.getId(o) })
    },
    objects () {
      let self = this
      return this.objectsData.results.map((o) => {
        let custom = self.customObjects.filter((co) => {
          return self.getId(co) === self.getId(o)
        })[0]
        if (custom) {
          return custom
        }
        return o
      })
    },
    labels () {
      return {
        refresh: this.$pgettext('Content/*/Button.Tooltip/Verb', 'Refresh table content'),
        selectAllItems: this.$pgettext('Content/*/Select/Verb', 'Select all items'),
        performAction: this.$pgettext('Content/*/Button.Label', 'Perform actions'),
        selectItem: this.$pgettext('Content/*/Select/Verb', 'Select')
      }
    },
    affectedObjectsCount () {
      if (this.selectAll) {
        return this.objectsData.count
      }
      return this.checked.length
    }
  },
  watch: {
    objectsData: {
      handler () {
        this.checked = []
        this.selectAll = false
      },
      deep: true
    },
    currentActionName () {
      // we update checked status as some actions have specific filters
      // on what is checkable or not
      let self = this
      this.checked = this.checked.filter(r => {
        return self.checkable.indexOf(r) > -1
      })
    }
  }
}
</script>
