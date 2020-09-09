<template>
  <main class="main pusher" v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div v-if="$store.state.auth.authenticated" class="ui small text container">
        <h2>
          <translate translate-context="Content/Login/Title">Are you sure you want to log out?</translate>
        </h2>
        <p v-translate="{username: $store.state.auth.username}" translate-context="Content/Login/Paragraph">You are currently logged in as %{ username }</p>
        <button class="ui button" @click="$store.dispatch('auth/logout')"><translate translate-context="Content/Login/Button.Label">Yes, log me out!</translate></button>
      </div>
      <div v-else class="ui small text container">
        <h2>
          <translate translate-context="Content/Login/Title">You aren't currently logged in</translate>
        </h2>
        <router-link to='/login' class="ui button"><translate translate-context="Content/Login/Button.Label">Log in!</translate></router-link>
      </div>
    </section>
  </main>
</template>

<script>
export default {
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/Login/Title', "Log Out")
      }
    }
  }
}
</script>
