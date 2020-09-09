<template>
  <main v-title="labels.users">
    <section class="ui vertical stripe segment">
      <h2 class="ui header">{{ labels.users }}</h2>
      <div class="ui hidden divider"></div>
      <users-table></users-table>
    </section>
  </main>
</template>

<script>
import UsersTable from "@/components/manage/users/UsersTable"

export default {
  components: {
    UsersTable
  },
  computed: {
    labels() {
      return {
        users: this.$pgettext('*/*/*/Noun', 'Users')
      }
    }
  }
}
</script>
