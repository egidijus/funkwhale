import json

from django import http

from .plugin import PLUGIN


@PLUGIN.register_api_view(path="prometheus")
def prometheus(request):
    stats = get_stats()
    return http.HttpResponse(json.dumps(stats))


def get_stats():
    return {"foo": "bar"}
