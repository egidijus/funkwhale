from django.conf.urls import url
from funkwhale_api.common import routers
from . import views

router = routers.OptionalSlashRouter()
router.register(r"users", views.UserViewSet, "users")

urlpatterns = [
    url(r"^users/login/?$", views.login, name="login"),
    url(r"^users/logout/?$", views.logout, name="logout"),
] + router.urls
