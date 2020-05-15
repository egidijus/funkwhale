<template>
  <main v-title="labels.invitations">
    <section class="ui vertical stripe segment">
      <h2 class="ui header">{{ labels.invitations }}</h2>
      <invitation-form></invitation-form>
      <div class="ui hidden divider"></div>
      <invitations-table></invitations-table>
    </section>
  </main>
</template>

<script>
import InvitationForm from "@/components/manage/users/InvitationForm"
import InvitationsTable from "@/components/manage/users/InvitationsTable"

export default {
  components: {
    InvitationForm,
    InvitationsTable
  },
  computed: {
    labels() {
      return {
        invitations: this.$pgettext('*/Admin/*/Noun', 'Invitations')
      }
    }
  }
}
</script>
