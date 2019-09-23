from funkwhale_api.common import admin

from . import models


@admin.register(models.Plugin)
class PluginAdmin(admin.ModelAdmin):
    list_display = ["name", "creation_date", "is_enabled"]
    list_filter = ["is_enabled"]
    list_select_related = True


@admin.register(models.UserPlugin)
class UserPluginAdmin(admin.ModelAdmin):
    list_display = ["plugin", "user", "creation_date", "is_enabled"]
    search_fields = ["user__username", "plugin__name"]
    list_filter = ["plugin__name", "is_enabled"]
    list_select_related = True
