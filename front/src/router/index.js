import Vue from "vue"
import Router from "vue-router"

Vue.use(Router)

console.log('PROCESS', process.env)
export default new Router({
  mode: "history",
  linkActiveClass: "active",
  base: process.env.VUE_APP_ROUTER_BASE_URL || "/",
  scrollBehavior(to, from, savedPosition) {
    if (to.meta.preserveScrollPosition) {
      return savedPosition
    }
    return new Promise(resolve => {
      setTimeout(() => {
        if (to.hash) {
          resolve({ selector: to.hash });
        }
        let pos = savedPosition || { x: 0, y: 0 };
        resolve(pos);
      }, 100);
    });
  },
  routes: [
    {
      path: "/",
      name: "index",
      component: () =>
        import(/* webpackChunkName: "core" */ "@/components/Home")
    },
    {
      path: "/front",
      name: "front",
      redirect: to => {
        const { hash, query } = to
        return { name: 'index', hash, query }
      }
    },
    {
      path: "/about",
      name: "about",
      component: () =>
        import(/* webpackChunkName: "about" */ "@/components/About")
    },
    {
      path: "/login",
      name: "login",
      component: () =>
        import(/* webpackChunkName: "login" */ "@/views/auth/Login"),
      props: route => ({ next: route.query.next || "/library" })
    },
    {
      path: "/notifications",
      name: "notifications",
      component: () =>
        import(/* webpackChunkName: "notifications" */ "@/views/Notifications")
    },
    {
      path: "/auth/password/reset",
      name: "auth.password-reset",
      component: () =>
        import(/* webpackChunkName: "password-reset" */ "@/views/auth/PasswordReset"),
      props: route => ({
        defaultEmail: route.query.email
      })
    },
    {
      path: "/auth/callback",
      name: "auth.callback",
      component: () =>
        import(/* webpackChunkName: "auth-callback" */ "@/views/auth/Callback"),
      props: route => ({
        code: route.query.code,
        state: route.query.state,
      })
    },
    {
      path: "/auth/email/confirm",
      name: "auth.email-confirm",
      component: () =>
        import(/* webpackChunkName: "signup" */ "@/views/auth/EmailConfirm"),
      props: route => ({
        defaultKey: route.query.key
      })
    },
    {
      path: "/search",
      name: "search",
      component: () =>
        import(/* webpackChunkName: "core" */ "@/views/Search"),
      props: route => ({
        initialId: route.query.id,
        type: route.query.type,
      })
    },
    {
      path: "/auth/password/reset/confirm",
      name: "auth.password-reset-confirm",
      component: () =>
        import(
          /* webpackChunkName: "password-reset" */ "@/views/auth/PasswordResetConfirm"
        ),
      props: route => ({
        defaultUid: route.query.uid,
        defaultToken: route.query.token
      })
    },
    {
      path: "/authorize",
      name: "authorize",
      component: () =>
        import(/* webpackChunkName: "settings" */ "@/components/auth/Authorize"),
      props: route => ({
        clientId: route.query.client_id,
        redirectUri: route.query.redirect_uri,
        scope: route.query.scope,
        responseType: route.query.response_type,
        nonce: route.query.nonce,
        state: route.query.state
      })
    },
    {
      path: "/signup",
      name: "signup",
      component: () =>
        import(/* webpackChunkName: "signup" */ "@/views/auth/Signup"),
      props: route => ({
        defaultInvitation: route.query.invitation
      })
    },
    {
      path: "/logout",
      name: "logout",
      component: () =>
        import(/* webpackChunkName: "login" */ "@/components/auth/Logout")
    },
    {
      path: "/settings",
      name: "settings",
      component: () =>
        import(/* webpackChunkName: "settings" */ "@/components/auth/Settings")
    },
    {
      path: "/settings/applications/new",
      name: "settings.applications.new",
      props: route => ({
        scopes: route.query.scopes,
        name: route.query.name,
        redirect_uris: route.query.redirect_uris
      }),
      component: () =>
        import(
          /* webpackChunkName: "settings" */ "@/components/auth/ApplicationNew"
        )
    },
    {
      path: "/settings/plugins",
      name: "settings.plugins",
      component: () =>
        import(
          /* webpackChunkName: "settings" */ "@/views/auth/Plugins"
        )
    },
    {
      path: "/settings/applications/:id/edit",
      name: "settings.applications.edit",
      component: () =>
        import(
          /* webpackChunkName: "settings" */ "@/components/auth/ApplicationEdit"
        ),
      props: true
    },
    ...[{suffix: '.full', path: '/@:username@:domain'}, {suffix: '', path: '/@:username'}].map((route) => {
      return {
        path: route.path,
        name: `profile${route.suffix}`,
        component: () =>
        import(/* webpackChunkName: "core" */ "@/views/auth/ProfileBase"),
        props: true,
        children: [
          {
            path: "",
            name: `profile${route.suffix}.overview`,
            component: () =>
              import(
                /* webpackChunkName: "core" */ "@/views/auth/ProfileOverview"
              )
          },
          {
            path: "activity",
            name: `profile${route.suffix}.activity`,
            component: () =>
              import(
                /* webpackChunkName: "core" */ "@/views/auth/ProfileActivity"
              )
          },
        ]
      }
    }),
    {
      path: "/favorites",
      name: "favorites",
      component: () =>
        import(/* webpackChunkName: "favorites" */ "@/components/favorites/List"),
      props: route => ({
        defaultOrdering: route.query.ordering,
        defaultPage: route.query.page,
        defaultPaginateBy: route.query.paginateBy
      })
    },
    {
      path: "/content",
      component: () =>
        import(/* webpackChunkName: "core" */ "@/views/content/Base"),
      children: [
        {
          path: "",
          name: "content.index",
          component: () =>
            import(/* webpackChunkName: "core" */ "@/views/content/Home")
        }
      ]
    },
    {
      path: "/content/libraries/tracks",
      component: () =>
        import(/* webpackChunkName: "auth-libraries" */ "@/views/content/Base"),
      children: [
        {
          path: "",
          name: "content.libraries.files",
          component: () =>
            import(
              /* webpackChunkName: "auth-libraries" */ "@/views/content/libraries/Files"
            ),
          props: route => ({
            query: route.query.q
          })
        }
      ]
    },
    {
      path: "/content/libraries",
      component: () =>
        import(/* webpackChunkName: "auth-libraries" */ "@/views/content/Base"),
      children: [
        {
          path: "",
          name: "content.libraries.index",
          component: () =>
            import(
              /* webpackChunkName: "auth-libraries" */ "@/views/content/libraries/Home"
            )
        }
      ]
    },
    {
      path: "/content/remote",
      component: () =>
        import(/* webpackChunkName: "auth-libraries" */ "@/views/content/Base"),
      children: [
        {
          path: "",
          name: "content.remote.index",
          component: () =>
            import(/* webpackChunkName: "auth-libraries" */ "@/views/content/remote/Home")
        }
      ]
    },
    {
      path: "/manage/settings",
      name: "manage.settings",
      component: () =>
        import(/* webpackChunkName: "admin" */ "@/views/admin/Settings")
    },
    {
      path: "/manage/library",
      component: () =>
        import(/* webpackChunkName: "admin" */ "@/views/admin/library/Base"),
      children: [
        {
          path: "edits",
          name: "manage.library.edits",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/EditsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "artists",
          name: "manage.library.artists",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/ArtistsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "artists/:id",
          name: "manage.library.artists.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/ArtistDetail"
            ),
          props: true
        },
        {
          path: "channels",
          name: "manage.channels",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/ChannelsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "channels/:id",
          name: "manage.channels.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/ChannelDetail"
            ),
          props: true
        },
        {
          path: "albums",
          name: "manage.library.albums",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/AlbumsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "albums/:id",
          name: "manage.library.albums.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/AlbumDetail"
            ),
          props: true
        },
        {
          path: "tracks",
          name: "manage.library.tracks",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/TracksList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "tracks/:id",
          name: "manage.library.tracks.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/TrackDetail"
            ),
          props: true
        },
        {
          path: "libraries",
          name: "manage.library.libraries",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/LibrariesList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "libraries/:id",
          name: "manage.library.libraries.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/LibraryDetail"
            ),
          props: true
        },
        {
          path: "uploads",
          name: "manage.library.uploads",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/UploadsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "uploads/:id",
          name: "manage.library.uploads.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/UploadDetail"
            ),
          props: true
        },
        {
          path: "tags",
          name: "manage.library.tags",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/TagsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "tags/:id",
          name: "manage.library.tags.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/library/TagDetail"
            ),
          props: true
        }
      ]
    },
    {
      path: "/manage/users",
      component: () =>
        import(/* webpackChunkName: "admin" */ "@/views/admin/users/Base"),
      children: [
        {
          path: "users",
          name: "manage.users.users.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/users/UsersList"
            )
        },
        {
          path: "invitations",
          name: "manage.users.invitations.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/users/InvitationsList"
            )
        }
      ]
    },
    {
      path: "/manage/moderation",
      component: () =>
        import(/* webpackChunkName: "admin" */ "@/views/admin/moderation/Base"),
      children: [
        {
          path: "domains",
          name: "manage.moderation.domains.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/DomainsList"
            )
        },
        {
          path: "domains/:id",
          name: "manage.moderation.domains.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/DomainsDetail"
            ),
          props: true
        },
        {
          path: "accounts",
          name: "manage.moderation.accounts.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/AccountsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q
            }
          }
        },
        {
          path: "accounts/:id",
          name: "manage.moderation.accounts.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/AccountsDetail"
            ),
          props: true
        },
        {
          path: "reports",
          name: "manage.moderation.reports.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/ReportsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q,
              updateUrl: true
            }
          }
        },
        {
          path: "reports/:id",
          name: "manage.moderation.reports.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/ReportDetail"
            ),
          props: true
        },
        {
          path: "requests",
          name: "manage.moderation.requests.list",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/RequestsList"
            ),
          props: route => {
            return {
              defaultQuery: route.query.q,
              updateUrl: true
            }
          }
        },
        {
          path: "requests/:id",
          name: "manage.moderation.requests.detail",
          component: () =>
            import(
              /* webpackChunkName: "admin" */ "@/views/admin/moderation/RequestDetail"
            ),
          props: true
        },
      ]
    },
    {
      path: "/library",
      component: () =>
        import(/* webpackChunkName: "core" */ "@/components/library/Library"),
      children: [
        {
          path: "",
          component: () =>
            import(/* webpackChunkName: "core" */ "@/components/library/Home"),
          name: "library.index"
        },
        {
          path: "me",
          component: () =>
            import(/* webpackChunkName: "core" */ "@/components/library/Home"),
          name: "library.me",
          props: route => ({
            scope: 'me',
          })
        },
        {
          path: "artists/",
          name: "library.artists.browse",
          component: () =>
            import(
              /* webpackChunkName: "artists" */ "@/components/library/Artists"
            ),
          props: route => ({
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultTags: Array.isArray(route.query.tag || [])
              ? route.query.tag
              : [route.query.tag],
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "me/artists",
          name: "library.artists.me",
          component: () =>
            import(
              /* webpackChunkName: "artists" */ "@/components/library/Artists"
            ),
          props: route => ({
            scope: 'me',
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultTags: Array.isArray(route.query.tag || [])
              ? route.query.tag
              : [route.query.tag],
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "albums/",
          name: "library.albums.browse",
          component: () =>
            import(
              /* webpackChunkName: "albums" */ "@/components/library/Albums"
            ),
          props: route => ({
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultTags: Array.isArray(route.query.tag || [])
              ? route.query.tag
              : [route.query.tag],
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "me/albums",
          name: "library.albums.me",
          component: () =>
            import(
              /* webpackChunkName: "albums" */ "@/components/library/Albums"
            ),
          props: route => ({
            scope: 'me',
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultTags: Array.isArray(route.query.tag || [])
              ? route.query.tag
              : [route.query.tag],
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "radios/",
          name: "library.radios.browse",
          component: () =>
            import(
              /* webpackChunkName: "radios" */ "@/components/library/Radios"
            ),
          props: route => ({
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "me/radios/",
          name: "library.radios.me",
          component: () =>
            import(
              /* webpackChunkName: "radios" */ "@/components/library/Radios"
            ),
          props: route => ({
            scope: 'me',
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "radios/build",
          name: "library.radios.build",
          component: () =>
            import(
              /* webpackChunkName: "radios" */ "@/components/library/radios/Builder"
            ),
          props: true
        },
        {
          path: "radios/build/:id",
          name: "library.radios.edit",
          component: () =>
            import(
              /* webpackChunkName: "radios" */ "@/components/library/radios/Builder"
            ),
          props: true
        },
        {
          path: "radios/:id",
          name: "library.radios.detail",
          component: () =>
            import(/* webpackChunkName: "radios" */ "@/views/radios/Detail"),
          props: true
        },
        {
          path: "playlists/",
          name: "library.playlists.browse",
          component: () =>
            import(/* webpackChunkName: "playlists" */ "@/views/playlists/List"),
          props: route => ({
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "me/playlists/",
          name: "library.playlists.me",
          component: () =>
            import(/* webpackChunkName: "playlists" */ "@/views/playlists/List"),
          props: route => ({
            scope: 'me',
            defaultOrdering: route.query.ordering,
            defaultQuery: route.query.query,
            defaultPaginateBy: route.query.paginateBy,
            defaultPage: route.query.page
          })
        },
        {
          path: "playlists/:id",
          name: "library.playlists.detail",
          component: () =>
            import(/* webpackChunkName: "playlists" */ "@/views/playlists/Detail"),
          props: route => ({
            id: route.params.id,
            defaultEdit: route.query.mode === "edit"
          })
        },
        {
          path: "tags/:id",
          name: "library.tags.detail",
          component: () =>
            import(
              /* webpackChunkName: "tags" */ "@/components/library/TagDetail"
            ),
          props: true
        },
        {
          path: "artists/:id",
          component: () =>
            import(
              /* webpackChunkName: "artists" */ "@/components/library/ArtistBase"
            ),
          props: true,
          children: [
            {
              path: "",
              name: "library.artists.detail",
              component: () =>
                import(
                  /* webpackChunkName: "artists" */ "@/components/library/ArtistDetail"
                )
            },
            {
              path: "edit",
              name: "library.artists.edit",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/ArtistEdit"
                )
            },
            {
              path: "edit/:editId",
              name: "library.artists.edit.detail",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/EditDetail"
                ),
              props: true
            }
          ]
        },
        {
          path: "albums/:id",
          component: () =>
            import(
              /* webpackChunkName: "albums" */ "@/components/library/AlbumBase"
            ),
          props: true,
          children: [
            {
              path: "",
              name: "library.albums.detail",
              component: () =>
                import(
                  /* webpackChunkName: "albums" */ "@/components/library/AlbumDetail"
                )
            },
            {
              path: "edit",
              name: "library.albums.edit",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/AlbumEdit"
                )
            },
            {
              path: "edit/:editId",
              name: "library.albums.edit.detail",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/EditDetail"
                ),
              props: true
            }
          ]
        },
        {
          path: "tracks/:id",
          component: () =>
            import(
              /* webpackChunkName: "tracks" */ "@/components/library/TrackBase"
            ),
          props: true,
          children: [
            {
              path: "",
              name: "library.tracks.detail",
              component: () =>
                import(
                  /* webpackChunkName: "tracks" */ "@/components/library/TrackDetail"
                )
            },
            {
              path: "edit",
              name: "library.tracks.edit",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/TrackEdit"
                )
            },
            {
              path: "edit/:editId",
              name: "library.tracks.edit.detail",
              component: () =>
                import(
                  /* webpackChunkName: "edits" */ "@/components/library/EditDetail"
                ),
              props: true
            }
          ]
        },
        {
          path: "uploads/:id",
          name: "library.uploads.detail",
          props: true,
          component: () =>
            import(
              /* webpackChunkName: "uploads" */ "@/components/library/UploadDetail"
            ),
        },
        {
          // browse a single library via it's uuid
          path: ":id([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
          props: true,
          component: () =>
            import(
              /* webpackChunkName: "library" */ "@/views/library/DetailBase"
            ),
          children: [
            {
              path: "",
              name: "library.detail",
              component: () =>
                import(
                  /* webpackChunkName: "library" */ "@/views/library/DetailOverview"
                )
            },
            {
              path: "albums",
              name: "library.detail.albums",
              component: () =>
                import(
                  /* webpackChunkName: "library" */ "@/views/library/DetailAlbums"
                )
            },
            {
              path: "tracks",
              name: "library.detail.tracks",
              component: () =>
                import(
                  /* webpackChunkName: "library" */ "@/views/library/DetailTracks"
                )
            },
            {
              path: "edit",
              name: "library.detail.edit",
              component: () =>
                import(
                  /* webpackChunkName: "auth-libraries" */ "@/views/library/Edit"
                )
            },
            {
              path: "upload",
              name: "library.detail.upload",
              component: () =>
                import(
                  /* webpackChunkName: "auth-libraries" */ "@/views/library/Upload"
                ),
              props: route => ({
                defaultImportReference: route.query.import
              })
            },
            // {
            //   path: "episodes",
            //   name: "library.detail.episodes",
            //   component: () =>
            //     import(
            //       /* webpackChunkName: "library" */ "@/views/library/DetailEpisodes"
            //     )
            // },
          ]
        }
      ]
    },
    {
      path: "/channels/:id",
      props: true,
      component: () =>
        import(
          /* webpackChunkName: "channels" */ "@/views/channels/DetailBase"
        ),
      children: [
        {
          path: "",
          name: "channels.detail",
          component: () =>
            import(
              /* webpackChunkName: "channels" */ "@/views/channels/DetailOverview"
            )
        },
        {
          path: "episodes",
          name: "channels.detail.episodes",
          component: () =>
            import(
              /* webpackChunkName: "channels" */ "@/views/channels/DetailEpisodes"
            )
        },
      ]
    },
    {
      path: "/subscriptions",
      name: "subscriptions",
      props: route => {
        return {
          defaultQuery: route.query.q
        }
      },
      component: () =>
        import(
          /* webpackChunkName: "channels-auth" */ "@/views/channels/SubscriptionsList"
        ),
    },
    {
      path: "*/index.html",
      redirect: "/"
    },
    {
      path: "*",
      component: () =>
        import(/* webpackChunkName: "core" */ "@/components/PageNotFound")
    }
  ]
})
