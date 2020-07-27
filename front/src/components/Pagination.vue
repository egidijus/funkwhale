<template>
  <div v-if='maxPage > 1' class="ui pagination menu component-pagination" role="navigation" :aria-label="labels.pagination">
    <a href
      :disabled="current - 1 < 1"
      :title="labels.previousPage"
      @click.prevent.stop="selectPage(current - 1)"
      :class="[{'disabled': current - 1 < 1}, 'item']"><i class="angle left icon"></i></a>
    <template v-if="!compact">
      <a href
        v-if="page !== 'skip'"
        v-for="page in pages"
        @click.prevent.stop="selectPage(page)"
        :class="[{'active': page === current}, 'item']">
        {{ page }}
      </a>
      <div v-else class="disabled item">
        …
      </div>
    </template>
    <a href
      :disabled="current + 1 > maxPage"
      :title="labels.nextPage"
      @click.prevent.stop="selectPage(current + 1)"
      :class="[{'disabled': current + 1 > maxPage}, 'item']"><i class="angle right icon"></i></a>
  </div>
</template>

<script>
import _ from "@/lodash"

export default {
  props: {
    current: { type: Number, default: 1 },
    paginateBy: { type: Number, default: 25 },
    total: { type: Number },
    compact: { type: Boolean, default: false }
  },
  computed: {
    labels() {
      return {
        pagination: this.$pgettext('Content/*/Hidden text/Noun', "Pagination"),
        previousPage: this.$pgettext('Content/*/Link', "Previous Page"),
        nextPage: this.$pgettext('Content/*/Link', "Next Page")
      }
    },
    pages: function() {
      let range = 2
      let current = this.current
      let beginning = _.range(1, Math.min(this.maxPage, 1 + range))
      let middle = _.range(
        Math.max(1, current - range + 1),
        Math.min(this.maxPage, current + range)
      )
      let end = _.range(this.maxPage, Math.max(1, this.maxPage - range))
      let allowed = beginning.concat(middle, end)
      allowed = _.uniq(allowed)
      allowed = _.sortBy(allowed, [
        e => {
          return e
        }
      ])
      let final = []
      allowed.forEach(p => {
        let last = final.slice(-1)[0]
        let consecutive = true
        if (last === "skip") {
          consecutive = false
        } else {
          if (!last) {
            consecutive = true
          } else {
            consecutive = last + 1 === p
          }
        }
        if (consecutive) {
          final.push(p)
        } else {
          if (p !== "skip") {
            final.push("skip")
            final.push(p)
          }
        }
      })
      return final
    },
    maxPage: function() {
      return Math.ceil(this.total / this.paginateBy)
    }
  },
  methods: {
    selectPage: function(page) {
      if (page > this.maxPage || page < 1) {
        return
      }
      if (this.current !== page) {
        this.$emit("page-changed", page)
      }
    }
  }
}
</script>
