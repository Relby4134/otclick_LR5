from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from surveys import views
urlpatterns = [path('admin/',admin.site.urls),path('',views.index,name='index'),path('surveys/<int:pk>/',views.detail,name='detail'),path('surveys/<int:pk>/results/',views.results,name='results'),path('responses/<int:pk>/',views.response_detail,name='response_detail'),path('thanks/',views.thanks,name='thanks')]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
