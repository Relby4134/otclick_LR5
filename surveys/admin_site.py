from django.contrib.admin.apps import AdminConfig
from django.contrib.admin.sites import AdminSite


class SurveyAdminSite(AdminSite):
    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        order = {'Survey': 0, 'Question': 1, 'Response': 2}
        for app in apps:
            if app['app_label'] == 'surveys':
                app['models'].sort(key=lambda model: order.get(model['object_name'], 99))
        return sorted(apps, key=lambda app: app['app_label'] != 'surveys')


class SurveyAdminConfig(AdminConfig):
    default_site = 'surveys.admin_site.SurveyAdminSite'
