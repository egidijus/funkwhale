from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from dynamic_preferences.registries import global_preferences_registry


def get_email_context():
    context = {}
    context["funkwhale_url"] = settings.FUNKWHALE_URL
    manager = global_preferences_registry.manager()
    context["funkwhale_site_name"] = (
        manager["instance__name"] or settings.FUNKWHALE_HOSTNAME
    )
    context["funkwhale_site_domain"] = settings.FUNKWHALE_HOSTNAME
    return context


class FunkwhaleAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        manager = global_preferences_registry.manager()
        return manager["users__registration_enabled"]

    def send_mail(self, template_prefix, email, context):
        context.update(get_email_context())
        return super().send_mail(template_prefix, email, context)

    def get_login_redirect_url(self, request):
        return "noop"

    def get_signup_redirect_url(self, request):
        return "noop"

    def add_message(self, *args, **kwargs):
        # disable message sending
        return
