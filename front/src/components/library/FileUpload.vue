  <template>
  <div class="component-file-upload">
    <div class="ui top attached tabular menu">
      <a :class="['item', {active: currentTab === 'summary'}]" @click="currentTab = 'summary'"><translate translate-context="Content/Library/Tab.Title/Short">Summary</translate></a>
      <a :class="['item', {active: currentTab === 'uploads'}]" @click="currentTab = 'uploads'">
        <translate translate-context="Content/Library/Tab.Title/Short">Uploading</translate>
        <div v-if="files.length === 0" class="ui label">
          0
        </div>
        <div v-else-if="files.length > uploadedFilesCount + erroredFilesCount" class="ui warning label">
          {{ uploadedFilesCount + erroredFilesCount }}/{{ files.length }}
        </div>
        <div v-else :class="['ui', {'success': erroredFilesCount === 0}, {'danger': erroredFilesCount > 0}, 'label']">
          {{ uploadedFilesCount + erroredFilesCount }}/{{ files.length }}
        </div>
      </a>
      <a :class="['item', {active: currentTab === 'processing'}]" @click="currentTab = 'processing'">
        <translate translate-context="Content/Library/Tab.Title/Short">Processing</translate>
        <div v-if="processableFiles === 0" class="ui label">
          0
        </div>
        <div v-else-if="processableFiles > processedFilesCount" class="ui warning label">
          {{ processedFilesCount }}/{{ processableFiles }}
        </div>
        <div v-else :class="['ui', {'success': uploads.errored === 0}, {'danger': uploads.errored > 0}, 'label']">
          {{ processedFilesCount }}/{{ processableFiles }}
        </div>
      </a>
    </div>
    <div :class="['ui', 'bottom', 'attached', 'segment', {hidden: currentTab != 'summary'}]">
      <h2 class="ui header"><translate translate-context="Content/Library/Title/Verb">Upload new tracks</translate></h2>
      <div class="ui message">
        <p><translate translate-context="Content/Library/Paragraph">You are about to upload music to your library. Before proceeding, please ensure that:</translate></p>
        <ul>
          <li v-if="library.privacy_level != 'me'">
            <translate translate-context="Content/Library/List item">You are not uploading copyrighted content in a public library, otherwise you may be infringing the law</translate>
          </li>
          <li>
            <translate translate-context="Content/Library/List item">The music files you are uploading are tagged properly.</translate>&nbsp;
            <a href="http://picard.musicbrainz.org/" target='_blank'><translate translate-context="Content/Library/Link">We recommend using Picard for that purpose.</translate></a>
          </li>
          <li>
            <translate translate-context="Content/Library/List item">The uploaded music files are in OGG, Flac or MP3 format</translate>
          </li>
        </ul>
      </div>

      <form class="ui form" @submit.prevent="currentTab = 'uploads'">
        <div class="fields">
          <div class="ui field">
            <label><translate translate-context="Content/Library/Input.Label/Noun">Import reference</translate></label>
            <p><translate translate-context="Content/Library/Paragraph">This reference will be used to group imported files together.</translate></p>
            <input name="import-ref" type="text" v-model="importReference" />
          </div>
        </div>

        <button type="submit" class="ui success button"><translate translate-context="Content/Library/Button.Label">Proceed</translate></button>
      </form>
    </div>
    <div :class="['ui', 'bottom', 'attached', 'segment', {hidden: currentTab != 'uploads'}]">
      <div :class="['ui', {loading: isLoadingQuota}, 'container']">
        <div :class="['ui', {red: remainingSpace === 0}, {warning: remainingSpace > 0 && remainingSpace <= 50}, 'small', 'statistic']">
          <div class="label">
            <translate translate-context="Content/Library/Paragraph">Remaining storage space</translate>
          </div>
          <div class="value">
            {{ remainingSpace * 1000 * 1000 | humanSize}}
          </div>
        </div>
        <file-upload-widget
          :class="['ui', 'icon', 'basic', 'button']"
          :post-action="uploadUrl"
          :multiple="true"
          :data="uploadData"
          :drop="true"
          :extensions="supportedExtensions"
          v-model="files"
          name="audio_file"
          :thread="1"
          @input-file="inputFile"
          ref="upload">
          <i class="upload icon"></i>&nbsp;
          <translate translate-context="Content/Library/Paragraph/Call to action">Click to select files to upload or drag and drop files or directories</translate>
          <br />
          <br />
          <i><translate translate-context="Content/Library/Paragraph" :translate-params="{extensions: supportedExtensions.join(', ')}">Supported extensions: %{ extensions }</translate></i>
        </file-upload-widget>
      </div>
      <div v-if="files.length > 0" class="table-wrapper">
        <div class="ui hidden divider"></div>
        <table class="ui unstackable table">
          <thead>
            <tr>
              <th class="ten wide"><translate translate-context="Content/Library/Table.Label">Filename</translate></th>
              <th><translate translate-context="Content/*/*/Noun">Size</translate></th>
              <th><translate translate-context="*/*/*">Status</translate></th>
              <th><translate translate-context="*/*/*">Actions</translate></th>
            </tr>
            <tr v-if="retryableFiles.length > 1">
              <th class="ten wide"></th>
              <th></th>
              <th></th>
              <th>
                <button class="ui right floated small basic button" @click.prevent="retry(retryableFiles)">
                  <translate translate-context="Content/Library/Table">Retry failed uploads</translate>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(file, index) in sortedFiles" :key="file.id">
              <td :title="file.name">{{ file.name | truncate(60) }}</td>
              <td>{{ file.size | humanSize }}</td>
              <td>
                <span v-if="file.error" class="ui tooltip" :data-tooltip="labels.tooltips[file.error]">
                  <span class="ui danger icon label">
                    <i class="question circle outline icon" /> {{ file.error }}
                  </span>
                </span>
                <span v-else-if="file.success" class="ui success label">
                  <translate translate-context="Content/Library/Table" key="1">Uploaded</translate>
                </span>
                <span v-else-if="file.active" class="ui warning label">
                  <translate translate-context="Content/Library/Table" key="2">Uploading…</translate>
                  ({{ parseInt(file.progress) }}%)
                </span>
                <span v-else class="ui label"><translate translate-context="Content/Library/*/Short" key="3">Pending</translate></span>
              </td>
              <td>
                <template v-if="file.error">
                  <button
                    class="ui tiny basic icon right floated button"
                    :title="labels.retry"
                    @click.prevent="retry([file])"
                    v-if="retryableFiles.indexOf(file) > -1">
                    <i class="redo icon"></i>
                  </button>
                </template>
                <template v-else-if="!file.success">
                  <button class="ui tiny basic danger icon right floated button" @click.prevent="$refs.upload.remove(file)"><i class="delete icon"></i></button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
    <div :class="['ui', 'bottom', 'attached', 'segment', {hidden: currentTab != 'processing'}]">
      <library-files-table
        :needs-refresh="needsRefresh"
        ordering-config-name="library.detail.upload"
        @fetch-start="needsRefresh = false"
        :filters="{import_reference: importReference}"
        :custom-objects="Object.values(uploads.objects)"></library-files-table>
    </div>
  </div>
</template>

<script>
import _ from "@/lodash"
import $ from "jquery";
import axios from "axios";
import logger from "@/logging";
import FileUploadWidget from "./FileUploadWidget";
import LibraryFilesTable from "@/views/content/libraries/FilesTable";
import moment from "moment";

export default {
  props: ["library", "defaultImportReference"],
  components: {
    FileUploadWidget,
    LibraryFilesTable
  },
  data() {
    let importReference = this.defaultImportReference || moment().format();
    this.$router.replace({ query: { import: importReference } });
    return {
      files: [],
      needsRefresh: false,
      currentTab: "summary",
      uploadUrl: this.$store.getters['instance/absoluteUrl']("/api/v1/uploads/"),
      importReference,
      isLoadingQuota: false,
      quotaStatus: null,
      uploads: {
        pending: 0,
        finished: 0,
        skipped: 0,
        errored: 0,
        objects: {}
      },
      processTimestamp: new Date()
    };
  },
  created() {
    this.fetchStatus();
    this.fetchQuota();
    this.$store.commit("ui/addWebsocketEventHandler", {
      eventName: "import.status_updated",
      id: "fileUpload",
      handler: this.handleImportEvent
    });
    window.onbeforeunload = e => this.onBeforeUnload(e);
  },
  destroyed() {
    this.$store.commit("ui/removeWebsocketEventHandler", {
      eventName: "import.status_updated",
      id: "fileUpload"
    });
    window.onbeforeunload = null;
  },
  methods: {
    onBeforeUnload(e = {}) {
      const returnValue = ('This page is asking you to confirm that you want to leave - data you have entered may not be saved.');
      if (!this.hasActiveUploads) return null;
      Object.assign(e, {
        returnValue,
      });
      return returnValue;
    },
    fetchQuota () {
      let self = this
      self.isLoadingQuota = true
      axios.get('users/users/me/').then((response) => {
        self.quotaStatus = response.data.quota_status
        self.isLoadingQuota = false
      })
    },
    inputFile(newFile, oldFile) {
      if (!newFile) {
        return
      }
      if (this.remainingSpace < newFile.size / (1000 * 1000)) {
        newFile.error = 'denied'
      } else {
        this.$refs.upload.active = true;
      }
    },
    fetchStatus() {
      let self = this;
      let statuses = ["pending", "errored", "skipped", "finished"];
      statuses.forEach(status => {
        axios
          .get("uploads/", {
            params: {
              import_reference: self.importReference,
              import_status: status,
              page_size: 1
            }
          })
          .then(response => {
            self.uploads[status] = response.data.count;
          });
      });
    },
    handleImportEvent(event) {
      let self = this;
      if (event.upload.import_reference != self.importReference) {
        return;
      }
      this.$nextTick(() => {
        self.uploads[event.old_status] -= 1;
        self.uploads[event.new_status] += 1;
        self.uploads.objects[event.upload.uuid] = event.upload;
        self.needsRefresh = true
      });
    },
    retry (files) {
      files.forEach((file) => {
        this.$refs.upload.update(file, {error: '', progress: '0.00'})
      })
      this.$refs.upload.active = true;

    }
  },
  computed: {
    supportedExtensions () {
      return this.$store.state.ui.supportedExtensions
    },
    labels() {
      let denied = this.$pgettext('Content/Library/Help text',
        "Upload denied, ensure the file is not too big and that you have not reached your quota"
      );
      let server = this.$pgettext('Content/Library/Help text',
        "Cannot upload this file, ensure it is not too big"
      );
      let network = this.$pgettext('Content/Library/Help text',
        "A network error occurred while uploading this file"
      );
      let timeout = this.$pgettext('Content/Library/Help text', "Upload timeout, please try again");
      let extension = this.$pgettext('Content/Library/Help text',
        "Invalid file type, ensure you are uploading an audio file. Supported file extensions are %{ extensions }"
      );
      return {
        tooltips: {
          denied,
          server,
          network,
          timeout,
          retry: this.$pgettext('*/*/*/Verb', "Retry"),
          extension: this.$gettextInterpolate(extension, {
            extensions: this.supportedExtensions.join(", ")
          })
        }
      };
    },
    uploadedFilesCount() {
      return this.files.filter(f => {
        return f.success;
      }).length;
    },
    uploadingFilesCount() {
      return this.files.filter(f => {
        return !f.success && !f.error;
      }).length;
    },
    erroredFilesCount() {
      return this.files.filter(f => {
        return f.error;
      }).length;
    },
    retryableFiles () {
      return this.files.filter(f => {
        return f.error;
      });
    },
    processableFiles() {
      return (
        this.uploads.pending +
        this.uploads.skipped +
        this.uploads.errored +
        this.uploads.finished +
        this.uploadedFilesCount
      );
    },
    processedFilesCount() {
      return (
        this.uploads.skipped + this.uploads.errored + this.uploads.finished
      );
    },
    uploadData: function() {
      return {
        library: this.library.uuid,
        import_reference: this.importReference
      };
    },
    sortedFiles() {
      // return errored files on top

      return _.sortBy(this.files.map(f => {
        let statusIndex = 0
        if (f.errored) {
          statusIndex = -1
        }
        if (f.success) {
          statusIndex = 1
        }
        f.statusIndex = statusIndex
        return f
      }), ['statusIndex', 'name'])
    },
    hasActiveUploads () {
      return this.sortedFiles.filter((f) => { return f.active }).length > 0
    },
    remainingSpace () {
      if (!this.quotaStatus) {
        return 0
      }
      return Math.max(0, this.quotaStatus.remaining - (this.uploadedSize / (1000 * 1000)))
    },
    uploadedSize () {
      let uploaded = 0
      this.files.forEach((f) => {
        if (!f.error) {
          uploaded += f.size * (f.progress / 100)
        }
      })
      return uploaded
    }
  },
  watch: {
    importReference: _.debounce(function() {
      this.$router.replace({ query: { import: this.importReference } });
    }, 500),
    remainingSpace (newValue) {
      if (newValue <= 0) {
        this.$refs.upload.active = false;
      }
    },
    'uploads.finished' (v, o) {
      if (v > o) {
        this.$emit('uploads-finished', v - o)
      }
    }
  }
};
</script>
