"""API routes. The router builds all list/detail URLs for each ViewSet."""
from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, TagViewSet, TaskViewSet, UserProfileViewSet

router = DefaultRouter()
router.register("profiles", UserProfileViewSet, basename="profile")
router.register("projects", ProjectViewSet, basename="project")
router.register("tags", TagViewSet, basename="tag")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
