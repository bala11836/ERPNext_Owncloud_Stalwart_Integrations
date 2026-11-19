from django.apps import AppConfig
class CloudSessionConfig(AppConfig):
    name = 'cloud_session'
    def ready(self):
        from django.conf import settings
        name = 'cloud_session.middleware.WorkspaceSessionMiddleware'
        if name not in settings.MIDDLEWARE:
            settings.MIDDLEWARE = [*settings.MIDDLEWARE, name]
