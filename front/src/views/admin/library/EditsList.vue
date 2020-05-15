<template>
  <main v-title="labels.title">
    <section class="ui vertical stripe segment">
      <edits-card-list :update-url="true" :default-query="defaultQuery">
        <h2 class="ui header"><translate translate-context="Content/Admin/Title/Noun">Library edits</translate></h2>
      </edits-card-list>
    </section>
  </main>
</template>

<script>
import EditsCardList from "@/components/manage/library/EditsCardList"

export default {
  props: {
    defaultQuery: {type: String, required: false},
  },
  components: {
    EditsCardList
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('*/Admin/*/Noun', 'Edits')
      }
    }
  }
}
</script>
