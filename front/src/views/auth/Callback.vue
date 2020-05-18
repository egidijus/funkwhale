<template>
  <main class="main pusher">
    <section class="ui vertical stripe segment">
      <div class="ui small text container">
        <div class="ui hidden divider"></div>
        <div class="ui active inverted dimmer">
          <div class="ui text loader">
            <h2><translate translate-context="*/Login/*">Logging in…</translate></h2> {{ next }} {{ code }} {{ state }}
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script>

export default {
  props: ["state", "code"],
  async mounted () {
    await this.$store.dispatch('auth/handleOauthCallback', this.code)
    this.$router.push(this.state || '/library')
  }
}
</script>
