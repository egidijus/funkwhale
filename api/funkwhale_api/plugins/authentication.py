from funkwhale_api import plugins


class AttachPluginsConfMixin(object):
    def authenticate(self, request):
        auth = super().authenticate(request)
        self.update_plugins_conf(request, auth)
        return auth

    def update_plugins_conf(self, request, auth):
        if auth:
            plugins.update_plugins_conf_with_user_settings(
                getattr(request, "plugins_conf", []), user=auth[0]
            )
