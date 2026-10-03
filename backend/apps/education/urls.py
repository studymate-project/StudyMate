from rest_framework.routers import DefaultRouter

from .views import (
    AcademicLevelViewSet,
    CourseViewSet,
    EducationBackgroundViewSet,
    InterestViewSet,
    StudentInterestViewSet,
)


router = DefaultRouter()
router.register(r"backgrounds", EducationBackgroundViewSet, basename="education-background")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"academic-levels", AcademicLevelViewSet, basename="academic-level")
router.register(r"levels", AcademicLevelViewSet, basename="level")
router.register(r"interests", InterestViewSet, basename="interest")
router.register(r"student-interests", StudentInterestViewSet, basename="student-interest")

urlpatterns = router.urls
