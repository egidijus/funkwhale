<template>
  <div>
    <div class="ui inline form">
      <div class="fields">
        <div class="ui six wide field">
          <label for="files-search">
            <translate translate-context="Content/Search/Input.Label/Noun">Search</translate>
          </label>
          <form @submit.prevent="search.query = $refs.search.value">
            <input
              name="search"
              ref="search"
              type="text"
              id="files-search"
              :value="search.query"
              :placeholder="labels.searchPlaceholder"
            />
          </form>
        </div>
        <div class="field">
          <label for="import-status">
            <translate translate-context="Content/*/*/Noun">Import status</translate>
          </label>
          <select
            id="import-status"
            class="ui dropdown"
            @change="addSearchToken('status', $event.target.value)"
            :value="getTokenValue('status', '')"
          >
            <option value>
              <translate translate-context="Content/*/Dropdown">All</translate>
            </option>
            <option value="draft">
              <translate translate-context="Content/Library/*/Short">Draft</translate>
            </option>
            <option value="pending">
              <translate translate-context="Content/Library/*/Short">Pending</translate>
            </option>
            <option value="skipped">
              <translate translate-context="Content/Library/*">Skipped</translate>
            </option>
            <option value="errored">
              <translate translate-context="Content/Library/Dropdown">Failed</translate>
            </option>
            <option value="finished">
              <translate translate-context="Content/Library/*">Finished</translate>
            </option>
          </select>
        </div>
        <div class="field">
          <label for="ordering-select">
            <translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering</translate>
          </label>
          <select id="ordering-select" class="ui dropdown" v-model="ordering">
            <option
              v-for="option in orderingOptions"
              :value="option[0]"
            >{{ sharedLabels.filters[option[1]] }}</option>
          </select>
        </div>
        <div class="field">
          <label for="ordering-direction">
            <translate translate-context="Content/Search/Dropdown.Label/Noun">Ordering direction</translate>
          </label>
          <select id="ordering-direction" class="ui dropdown" v-model="orderingDirection">
            <option value="+">
              <translate translate-context="Content/Search/Dropdown">Ascending</translate>
            </option>
            <option value="-">
              <translate translate-context="Content/Search/Dropdown">Descending</translate>
            </option>
          </select>
        </div>
      </div>
    </div>
    <import-status-modal :upload="detailedUpload" :show.sync="showUploadDetailModal" />
    <div class="dimmable">
      <div v-if="isLoading" class="ui active inverted dimmer">
        <div class="ui loader"></div>
      </div>
      <div v-else-if="!result && result.results.length === 0 && !needsRefresh" class="ui placeholder segment">
        <div class="ui icon header">
          <i class="upload icon"></i>
          <translate
          translate-context="Content/Home/Placeholder"
          >No tracks have been added to this library yet</translate>
        </div>
      </div>
      <action-table
        v-else
        @action-launched="fetchData"
        :id-field="'uuid'"
        :objects-data="result"
        :custom-objects="customObjects"
        :actions="actions"
        :refreshable="true"
        :needs-refresh="needsRefresh"
        :action-url="'uploads/action/'"
        @refresh="fetchData"
        :filters="actionFilters"
      >
        <template slot="header-cells">
          <th>
            <translate translate-context="*/*/*/Noun">Title</translate>
          </th>
          <th>
            <translate translate-context="*/*/*/Noun">Artist</translate>
          </th>
          <th>
            <translate translate-context="*/*/*">Album</translate>
          </th>
          <th>
            <translate translate-context="*/*/*/Noun">Upload date</translate>
          </th>
          <th>
            <translate translate-context="Content/*/*/Noun">Import status</translate>
          </th>
          <th>
            <translate translate-context="Content/*/*">Duration</translate>
          </th>
          <th>
            <translate translate-context="Content/*/*/Noun">Size</translate>
          </th>
        </template>
        <template slot="row-cells" slot-scope="scope">
          <template v-if="scope.obj.track">
            <td>
              <router-link :to="{name: 'library.tracks.detail', params: {id: scope.obj.track.id }}">
                {{ scope.obj.track.title|truncate(25) }}
              </router-link>
            </td>
            <td>
              <a
                href=""
                class="discrete link"
                @click.prevent="addSearchToken('artist', scope.obj.track.artist.name)"
              >{{ scope.obj.track.artist.name|truncate(20) }}</a>
            </td>
            <td>
              <a
                href=""
                v-if="scope.obj.track.album"
                class="discrete link"
                @click.prevent="addSearchToken('album', scope.obj.track.album.title)"
              >{{ scope.obj.track.album.title|truncate(20) }}</a>
            </td>
          </template>
          <template v-else>
            <td :title="scope.obj.source">{{ scope.obj.source | truncate(25) }}</td>
            <td></td>
            <td></td>
          </template>
          <td>
            <human-date :date="scope.obj.creation_date"></human-date>
          </td>
          <td>
            <a 
              href=""
              class="discrete link"
              @click.prevent="addSearchToken('status', scope.obj.import_status)"
              :title="sharedLabels.fields.import_status.choices[scope.obj.import_status].help"
            >{{ sharedLabels.fields.import_status.choices[scope.obj.import_status].label }}</a>
            <button
              class="ui tiny basic icon button"
              :title="sharedLabels.fields.import_status.detailTitle"
              :aria-label="labels.showStatus"
              @click="detailedUpload = scope.obj; showUploadDetailModal = true"
            >
              <i class="question circle outline icon"></i>
            </button>
          </td>
          <td v-if="scope.obj.duration">{{ scope.obj.duration | duration }}</td>
          <td v-else>
            <translate translate-context="*/*/*">N/A</translate>
          </td>
          <td v-if="scope.obj.size">{{ scope.obj.size | humanSize }}</td>
          <td v-else>
            <translate translate-context="*/*/*">N/A</translate>
          </td>
        </template>
      </action-table>
    </div>
    <div>
      <pagination
        v-if="result && result.count > paginateBy"
        @page-changed="page = $event; fetchData()"
        :compact="true"
        :current="page"
        :paginate-by="paginateBy"
        :total="result.count"
      ></pagination>

      <span v-if="result && result.results.length > 0">
        <translate
          translate-context="Content/*/Paragraph"
          :translate-params="{start: ((page-1) * paginateBy) + 1, end: ((page-1) * paginateBy) + result.results.length, total: result.count}"
        >Showing results %{ start }-%{ end } on %{ total }</translate>
      </span>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import _ from "@/lodash";
import time from "@/utils/time";
import { normalizeQuery, parseTokens } from "@/search";

import Pagination from "@/components/Pagination";
import ActionTable from "@/components/common/ActionTable";
import OrderingMixin from "@/components/mixins/Ordering";
import TranslationsMixin from "@/components/mixins/Translations";
import SmartSearchMixin from "@/components/mixins/SmartSearch";
import ImportStatusModal from "@/components/library/ImportStatusModal";

export default {
  mixins: [OrderingMixin, TranslationsMixin, SmartSearchMixin],
  props: {
    filters: { type: Object, required: false },
    needsRefresh: { type: Boolean, required: false, default: false },
    customObjects: {
      type: Array,
      required: false,
      default: () => {
        return [];
      }
    }
  },
  components: {
    Pagination,
    ActionTable,
    ImportStatusModal
  },
  data() {
    return {
      time,
      detailedUpload: null,
      showUploadDetailModal: false,
      isLoading: false,
      result: null,
      page: 1,
      search: {
        query: this.defaultQuery,
        tokens: parseTokens(normalizeQuery(this.defaultQuery))
      },
      orderingOptions: [
        ["creation_date", "creation_date"],
        ["title", "track_title"],
        ["size", "size"],
        ["duration", "duration"],
        ["bitrate", "bitrate"],
        ["album_title", "album_title"],
        ["artist_name", "artist_name"]
      ]
    };
  },
  created() {
    this.fetchData();
  },
  methods: {
    fetchData() {
      this.$emit("fetch-start");
      let params = _.merge(
        {
          page: this.page,
          page_size: this.paginateBy,
          ordering: this.getOrderingAsString(),
          q: this.search.query,
          include_channels: 'true',
        },
        this.filters || {}
      );
      let self = this;
      self.isLoading = true;
      self.checked = [];
      axios.get("/uploads/", { params: params }).then(
        response => {
          self.result = response.data;
          self.isLoading = false;
        },
        error => {
          self.isLoading = false;
          self.errors = error.backendErrors;
        }
      );
    },
  },
  computed: {
    labels() {
      return {
        searchPlaceholder: this.$pgettext(
          "Content/Library/Input.Placeholder",
          "Search by title, artist, album…"
        ),
        showStatus: this.$pgettext('Content/Library/Button.Label/Verb', 'Show information about the upload status for this track')
      };
    },
    actionFilters() {
      var currentFilters = {
        q: this.search.query,
        include_channels: 'true',
      };
      if (this.filters) {
        return _.merge(currentFilters, this.filters);
      } else {
        return currentFilters;
      }
    },
    actions() {
      let deleteMsg = this.$pgettext("*/*/*/Verb", "Delete");
      let relaunchMsg = this.$pgettext(
        "Content/Library/Dropdown/Verb",
        "Restart import"
      );
      return [
        {
          name: "delete",
          label: deleteMsg,
          isDangerous: true,
          allowAll: true
        },
        {
          name: "relaunch_import",
          label: relaunchMsg,
          isDangerous: true,
          allowAll: true,
          filterCheckable: f => {
            return f.import_status != "finished";
          }
        }
      ];
    }
  },
  watch: {
    orderingDirection: function() {
      this.page = 1;
      this.fetchData();
    },
    page: function() {
      this.fetchData();
    },
    ordering: function() {
      this.page = 1;
      this.fetchData();
    },
    search(newValue) {
      this.page = 1;
      this.fetchData();
    }
  }
};
</script>
