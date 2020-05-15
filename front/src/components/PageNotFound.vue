<template>
  <main class="main pusher" :v-title="labels.title">
    <section class="ui vertical stripe segment">
      <div class="ui text container">
        <h1 class="ui huge header">
          <i class="warning icon"></i>
          <div class="content">
            <translate translate-context="Content/*/Title">Page not found!</translate>
          </div>
        </h1>
        <p><translate translate-context="Content/*/Paragraph">Sorry, the page you asked for does not exist:</translate></p>
        <a :href="path">{{ path }}</a>
        <div class="ui hidden divider"></div>
        <router-link class="ui icon labeled right button" to="/">
          <translate translate-context="Content/*/Button.Label/Verb">Go to home page</translate>
          <i class="right arrow icon"></i>
        </router-link>
      </div>
    </section>
  </main>
</template>

<script>
export default {
  data: function() {
    return {
      path: window.location.href
    }
  },
  computed: {
    labels() {
      return {
        title: this.$pgettext('Head/*/Title', "Page Not Found")
      }
    }
  }
}
</script>
