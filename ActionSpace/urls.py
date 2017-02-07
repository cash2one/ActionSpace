"""ActionSpace URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import RedirectView
from ActionSpace.view import UserViewSet, GroupViewSet, ServerViewSet, MachineViewSet, ok, login, guest_login
from rest_framework import routers
from django.conf import settings

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'servers', ServerViewSet)
router.register(r'machines', MachineViewSet)

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='om:index', permanent=False), name='index'),
    url(r'^ok$', ok, name='ok'),
    url(r'^login/$', login, name='login'),
    url(r'^guest_login/$', guest_login, name='guest_login'),
    url(r'^api/', include(router.urls)),
    url(r'^om/', include('om.urls', namespace='om')),
    url(r'^switch/', include('switch.urls', namespace='switch')),
    url(r'^utils/', include('utils.urls', namespace='utils')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^select2/', include('django_select2.urls')),
]

if settings.DEBUG and settings.USE_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]


