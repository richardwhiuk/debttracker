from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

def drl(regex, name):
  return url(regex, 'debt.views.' + name, name=name)

urlpatterns = patterns('',
    # Examples:
    #url(r'^$', 'debt.views.home', name='home'),
    drl(r'^(?P<instance_id>\d+)/summary/$', 'summary'),
    drl(r'^(?P<instance_id>\d+)/detailed/$', 'detailed'),
    drl(r'^(?P<instance_id>\d+)/individual/$', 'individual'),
    drl(r'^(?P<instance_id>\d+)/changes/$', 'changes'),
    drl(r'^(?P<instance_id>\d+)/entries/$', 'entries'),
    drl(r'^(?P<instance_id>\d+)/add/$', 'add_entry'),
    drl(r'^(?P<instance_id>\d+)/add/advanced/$', 'add_entry_advanced'),
    drl(r'^(?P<instance_id>\d+)/add/person/$', 'add_person'),
    drl(r'^(?P<instance_id>\d+)/delete/state/(?P<state_id>\d+)/$', 'delete_state'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

