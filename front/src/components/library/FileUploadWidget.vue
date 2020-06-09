<script>
import FileUpload from 'vue-upload-component'
import {setCsrf} from '@/utils'

export default {
  extends: FileUpload,
  methods: {
    uploadHtml5 (file) {
      let form = new window.FormData()
      let filename = file.file.filename || file.name
      let value
      let data = {...file.data}
      if (data.import_metadata) {
        data.import_metadata = {...(data.import_metadata || {})}
        if (data.channel && !data.import_metadata.title) {
          data.import_metadata.title = filename.replace(/\.[^/.]+$/, "")
        }
        data.import_metadata = JSON.stringify(data.import_metadata)
      }
      for (let key in data) {
        value = data[key]
        if (value &&   typeof value === 'object' && typeof value.toString !== 'function') {
          if (value instanceof File) {
            form.append(key, value, value.name)
          } else {
            form.append(key, JSON.stringify(value))
          }
        } else if (value !== null && value !== undefined) {
          form.append(key, value)
        }
      }
      form.append('source', `upload://${filename}`)
      form.append(this.name, file.file, filename)
      let xhr = new XMLHttpRequest()
      xhr.open('POST', file.postAction)
      setCsrf(xhr)
      if (this.$store.state.auth.oauth.accessToken) {
        xhr.setRequestHeader('Authorization', this.$store.getters['auth/header'])
      }
      return this.uploadXhr(xhr, file, form)
    }
  }
}
</script>
