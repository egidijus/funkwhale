<template>
  <main v-title="labels.accounts">
    <section class="ui vertical stripe segment">
      <h2 class="ui header"><translate translate-context="*/Moderation/Title">Accounts</translate></h2>
      <div class="ui hidden divider"></div>
      <accounts-table :update-url="true" :default-query="defaultQuery"></accounts-table>
    </section>
  </main>
</template>

<script>
import AccountsTable from "@/components/manage/moderation/AccountsTable"

export default {
  components: {
    AccountsTable
  },
  props: {
    defaultQuery: {type: String, required: false},
  },
  computed: {
    labels() {
      return {
        accounts: this.$pgettext('*/Moderation/Title', "Accounts")
      }
    }
  }
}
</script>
