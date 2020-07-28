from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.SimpleRouter(trailing_slash=False)
music_router = routers.SimpleRouter(trailing_slash=False)
index_router = routers.SimpleRouter(trailing_slash=False)

router.register(r"federation/shared", views.SharedViewSet, "shared")
router.register(r"federation/actors", views.ActorViewSet, "actors")
router.register(r"federation/edits", views.EditViewSet, "edits")
router.register(r"federation/reports", views.ReportViewSet, "reports")
router.register(r".well-known", views.WellKnownViewSet, "well-known")

music_router.register(r"libraries", views.MusicLibraryViewSet, "libraries")
music_router.register(r"uploads", views.MusicUploadViewSet, "uploads")
music_router.register(r"artists", views.MusicArtistViewSet, "artists")
music_router.register(r"albums", views.MusicAlbumViewSet, "albums")
music_router.register(r"tracks", views.MusicTrackViewSet, "tracks")


index_router.register(r"index", views.IndexViewSet, "index")

urlpatterns = router.urls + [
    url("federation/music/", include((music_router.urls, "music"), namespace="music")),
    url("federation/", include((index_router.urls, "index"), namespace="index")),
]
