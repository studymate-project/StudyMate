from django.urls import include, path

from apps.resources.views import SavedResourceListView

from .views import SearchView, api_root, health

urlpatterns = [
    path('', api_root, name='api-root'),
    path('health/', health, name='health'),
    path('search/', SearchView.as_view(), name='search'),
    path('auth/', include('apps.core.reserved_urls')),
    path('saved-resources/', SavedResourceListView.as_view(), name='saved-resources'),
    path('users/', include('apps.users.urls')),
    path('education/', include('apps.education.urls')),
    path('resources/', include('apps.resources.urls')),
    path('videos/', include('apps.resources.video_urls')),
    path('questions/', include('apps.community.urls')),
    path('notifications/', include('apps.notifications.urls')),
]
