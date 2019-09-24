from funkwhale_api import plugins


class AttachPluginsConfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        plugins.attach_plugins_conf(request)
        return self.get_response(request)
