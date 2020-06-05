<template>
  <div class="ui fluid category search">
    <slot></slot><div class="ui icon input">
      <input ref="search" type="search" class="prompt" name="search" :placeholder="labels.placeholder" @keydown.esc="$event.target.blur()">
      <i class="search icon"></i>
    </div>
    <div class="results"></div>
    <slot name="after"></slot>
    <GlobalEvents
      @keydown.shift.f.prevent.exact="focusSearch"
    />
  </div>
</template>

<script>
import jQuery from 'jquery'
import router from '@/router'
import lodash from '@/lodash'
import GlobalEvents from "@/components/utils/global-events"

export default {
  components: {
  GlobalEvents,
  },
  computed: {
    labels () {
      return {
        placeholder: this.$pgettext('Sidebar/Search/Input.Placeholder', 'Search for artists, albums, tracks…')
      }
    }
  },
  mounted () {
    let artistLabel = this.$pgettext('*/*/*/Noun', 'Artist')
    let albumLabel = this.$pgettext('*/*/*', 'Album')
    let trackLabel = this.$pgettext('*/*/*/Noun', 'Track')
    let tagLabel = this.$pgettext('*/*/*/Noun', 'Tag')
    let self = this
    var searchQuery;

    jQuery(this.$el).keypress(function(e) {
      if(e.which == 13) {
        // Cancel any API search request to backend…
        jQuery(this.$el).search('cancel query');
        // Go direct to the artist page…
        router.push("/library/artists?query=" + searchQuery + "&page=1&paginateBy=25&ordering=name");
	}
    });


    jQuery(this.$el).search({
      type: 'category',
      minCharacters: 3,
      showNoResults: true,
      error: {
        noResultsHeader: this.$pgettext('Sidebar/Search/Error', 'No matches found'),
        noResults: this.$pgettext('Sidebar/Search/Error.Label', 'Sorry, there are no results for this search')
      },
      onSelect (result, response) {
        jQuery(self.$el).search("set value", searchQuery)
        router.push(result.routerUrl)
        jQuery(self.$el).search("hide results")
        return false
      },
      onSearchQuery (query) {
        self.$emit('search')
        searchQuery = query
      },
      apiSettings: {
        beforeXHR: function (xhrObject) {
          if (!self.$store.state.auth.authenticated) {
            return xhrObject
          }
          xhrObject.setRequestHeader('Authorization', self.$store.getters['auth/header'])
          return xhrObject
        },
        onResponse: function (initialResponse) {
          let objId = self.extractObjId(searchQuery)
          let results = {}
          let isEmptyResults = true
          let categories = [
            {
              code: 'federation',
              name: self.$pgettext('*/*/*', 'Federation'),
            },
            {
              code: 'podcasts',
              name: self.$pgettext('*/*/*', 'Podcasts'),
            },
            {
              code: 'artists',
              route: 'library.artists.detail',
              name: artistLabel,
              getTitle (r) {
                return r.name
              },
              getDescription (r) {
                return ''
              },
              getId (t) {
                return t.id
              }
            },
            {
              code: 'albums',
              route: 'library.albums.detail',
              name: albumLabel,
              getTitle (r) {
                return r.title
              },
              getDescription (r) {
                return r.artist.name
              },
              getId (t) {
                return t.id
              }
            },
            {
              code: 'tracks',
              route: 'library.tracks.detail',
              name: trackLabel,
              getTitle (r) {
                return r.title
              },
              getDescription (r) {
                if (r.album) {
                  return `${r.album.artist.name} - ${r.album.title}`
                } else {
                  return r.artist.name
                }
              },
              getId (t) {
                return t.id
              }
            },
            {
              code: 'tags',
              route: 'library.tags.detail',
              name: tagLabel,
              getTitle (r) {
                return `#${r.name}`
              },
              getDescription (r) {
                return ''
              },
              getId (t) {
                return t.name
              }
            }
          ]
          categories.forEach(category => {
            results[category.code] = {
              name: category.name,
              results: []
            }
            if (category.code === 'federation') {

              if (objId) {
                isEmptyResults = false
                let searchMessage = self.$pgettext('Search/*/*', 'Search on the fediverse')
                results['federation'] = {
                  name: self.$pgettext('*/*/*', 'Federation'),
                  results: [{
                    title: searchMessage,
                    routerUrl: {
                      name: 'search',
                      query: {
                        id: objId,
                      }
                    }
                  }]
                }
              }
            }
            else if (category.code === 'podcasts') {
              if (objId) {
                isEmptyResults = false
                let searchMessage = self.$pgettext('Search/*/*', 'Subscribe to podcast via RSS')
                results['podcasts'] = {
                  name: self.$pgettext('*/*/*', 'Podcasts'),
                  results: [{
                    title: searchMessage,
                    routerUrl: {
                      name: 'search',
                      query: {
                        id: objId,
                        type: "rss"
                      }
                    }
                  }]
                }
              }
            }
            else {
              initialResponse[category.code].forEach(result => {
                isEmptyResults = false
                let id = category.getId(result)
                results[category.code].results.push({
                  title: category.getTitle(result),
                  id,
                  routerUrl: {
                    name: category.route,
                    params: {
                      id
                    }
                  },
                  description: category.getDescription(result)
                })
              })
            }
          })
          return {
            results: isEmptyResults ? {} : results
          }
        },
        url: this.$store.getters['instance/absoluteUrl']('api/v1/search?query={query}')
      }
    })
  },
  methods: {
    focusSearch () {
      this.$refs.search.focus()
    },
    extractObjId (query) {
      query = lodash.trim(query)
      query = lodash.trim(query, '@')
      if (query.indexOf(' ') > -1) {
        return
      }
      if (query.startsWith('http://') || query.startsWith('https://')) {
        return query
      }
      if (query.split('@').length > 1) {
        return query
      }
    }
  }
}
</script>
