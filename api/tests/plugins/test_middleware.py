from django.http import HttpResponse

from funkwhale_api.plugins import middleware


def test_attach_plugins_conf_middleware(mocker):
    attach_plugins_conf = mocker.patch("funkwhale_api.plugins.attach_plugins_conf")

    get_response = mocker.Mock()
    get_response.return_value = mocker.Mock(status_code=200)
    request = mocker.Mock(path="/")
    m = middleware.AttachPluginsConfMiddleware(get_response)

    assert m(request) == get_response.return_value
    attach_plugins_conf.assert_called_once_with(request)
