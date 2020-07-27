<template>
  <section>
    <channel-entries :limit="25" :filters="{channel: object.uuid, ordering: 'creation_date'}">
    </channel-entries>
  </section>
</template>

<script>
import ChannelEntries from "@/components/audio/ChannelEntries"


export default {
  props: ['object'],
  components: {
    ChannelEntries,
  },
}
</script>
