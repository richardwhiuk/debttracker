from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    #url(r'^$', 'debt.views.home', name='home'),
    url(r'^(?P<instance_id>\d+)/summary/$', 'debt.views.summary', name='summary'),
    url(r'^(?P<instance_id>\d+)/detailed/$', 'debt.views.detailed', name='detailed'),
    url(r'^(?P<instance_id>\d+)/changes/$', 'debt.views.changes', name='changes'),
    url(r'^(?P<instance_id>\d+)/entries/$', 'debt.views.entries', name='entries'),
    url(r'^(?P<instance_id>\d+)/add/(?P<mode>((advanced/)?))$', 'debt.views.add', name='add'),
    # url(r'^debt/', include('debt.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

