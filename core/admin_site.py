"""
Grouping for the admin index and sidebar.

The project registers ~50 models across 15 apps. Listed one app per block they
are a flat wall in INSTALLED_APPS order, which says nothing about how the site
is run, so both the index and the nav sidebar are regrouped by what a model is
*for* rather than which app happens to hold it.

To change the grouping, edit MODEL_GROUPS below: it is keyed by
"app_label.model_name" and its insertion order is also the order models appear
within their group. Anything not listed falls into "Other", so a newly
registered model can never quietly vanish off the index.
"""

from django.contrib import admin
from django.utils.text import slugify

CONTENT = "Content"
TEACHING = "Teaching"
STUDENTS = "Students & access"
ACTIVITY = "Student activity"
SITE = "Site & outreach"
RARE = "Rarely used"
OTHER = "Other"

# Top-to-bottom order of the groups on the index page.
GROUP_ORDER = [CONTENT, TEACHING, STUDENTS, ACTIVITY, SITE, RARE, OTHER]

MODEL_GROUPS = {
    # --- Content: everything a student is eventually shown ---------------
    "interactive_lessons.topic": CONTENT,
    "interactive_lessons.section": CONTENT,
    "interactive_lessons.question": CONTENT,
    "interactive_lessons.questionpart": CONTENT,
    "exam_papers.exampaper": CONTENT,
    "exam_papers.examquestion": CONTENT,
    "exam_papers.examquestionpart": CONTENT,
    "quickkicks.quickkick": CONTENT,
    "flashcards.flashcardset": CONTENT,
    "flashcards.flashcard": CONTENT,
    "notes.note": CONTENT,
    "revision.revisionmodule": CONTENT,
    "revision.revisionsection": CONTENT,
    "cheatsheets.cheatsheet": CONTENT,
    "hw_solutions.hwsolution": CONTENT,
    "hw_solutions.hwsolutionpage": CONTENT,
    "hw_solutions.hwsolutionsection": CONTENT,
    # --- Teaching: what a teacher sets up and marks ----------------------
    "homework.teacherprofile": TEACHING,
    "homework.teacherclass": TEACHING,
    "homework.homeworkassignment": TEACHING,
    "homework.homeworktask": TEACHING,
    "homework_check.homeworkcheck": TEACHING,
    "reports.timetableslot": TEACHING,
    "reports.classsession": TEACHING,
    "reports.classtest": TEACHING,
    "reports.studentclassnote": TEACHING,
    "reports.commentpreset": TEACHING,
    # --- Students & access ----------------------------------------------
    "auth.user": STUDENTS,
    "auth.group": STUDENTS,
    "students.studentprofile": STUDENTS,
    "students.registrationcode": STUDENTS,
    "account.emailaddress": STUDENTS,
    # --- Student activity: records of what students did ------------------
    "students.questionattempt": ACTIVITY,
    "exam_papers.examattempt": ACTIVITY,
    "exam_papers.examquestionattempt": ACTIVITY,
    "flashcards.flashcardattempt": ACTIVITY,
    "quickkicks.quickkickview": ACTIVITY,
    "homework.studenthomeworkprogress": ACTIVITY,
    "homework.homeworksubmission": ACTIVITY,
    "students.worksubmission": ACTIVITY,
    "notes.infobotquery": ACTIVITY,
    "interactive_lessons.studentinquiry": ACTIVITY,
    "students.questionfeedback": ACTIVITY,
    "exam_papers.examquestionfeedback": ACTIVITY,
    # --- Site & outreach -------------------------------------------------
    "home.newsitem": SITE,
    "core.subject": SITE,
    "schools.school": SITE,
    "schools.emaillog": SITE,
    # --- Rarely used: kept registered, just out of the way ---------------
    "students.loginhistory": RARE,
    "students.usersession": RARE,
    "notes.infobotfeedback": RARE,
    "homework.homeworknotificationsnooze": RARE,
    "sites.site": RARE,
    "socialaccount.socialapp": RARE,
    "socialaccount.socialaccount": RARE,
    "socialaccount.socialtoken": RARE,
    "markdownx.markdownximage": RARE,
}

# Position within a group is the order the key appears in MODEL_GROUPS.
_MODEL_POSITION = {key: i for i, key in enumerate(MODEL_GROUPS)}


def _model_key(model_dict):
    """"app_label.model_name" for a model dict from _build_app_dict()."""
    model = model_dict.get("model")
    if model is None:  # pragma: no cover - defensive against Django internals
        return ""
    return f"{model._meta.app_label}.{model._meta.model_name}"


class NumScoilAdminSite(admin.AdminSite):
    site_header = "NumScoil Administration"
    site_title = "NumScoil Admin"
    index_title = "Site management"

    def get_app_list(self, request, app_label=None):
        # App index pages (/admin/exam_papers/) and every breadcrumb ask for a
        # single app; those must keep the stock per-app behaviour.
        if app_label is not None:
            return super().get_app_list(request, app_label)

        grouped = {}
        for app in super().get_app_list(request):
            for model_dict in app["models"]:
                key = _model_key(model_dict)
                # The app name no longer appears as a heading, so keep it on
                # the row for the collisions it used to disambiguate.
                model_dict = dict(model_dict, app_name=app["name"])
                grouped.setdefault(MODEL_GROUPS.get(key, OTHER), []).append(
                    (_MODEL_POSITION.get(key, len(_MODEL_POSITION)), model_dict)
                )

        app_list = []
        for group in GROUP_ORDER:
            models = grouped.pop(group, None)
            if not models:
                continue
            models.sort(key=lambda item: (item[0], item[1]["name"]))
            app_list.append(
                {
                    "name": group,
                    "app_label": slugify(group),
                    # Must not be empty and must not appear in any admin path,
                    # or app_list.html marks every group as the current one.
                    "app_url": f"#{slugify(group)}",
                    "has_module_perms": True,
                    "models": _disambiguate([m for _, m in models]),
                }
            )
        return app_list


def _disambiguate(model_dicts):
    """
    Qualify duplicate labels with their app name.

    Model names only had to be unique within an app; grouping mixes apps
    together, so two "Sections" can now land side by side.
    """
    seen = {}
    for model_dict in model_dicts:
        seen.setdefault(model_dict["name"], []).append(model_dict)
    for name, clashing in seen.items():
        if len(clashing) > 1:
            for model_dict in clashing:
                model_dict["name"] = f"{name} ({model_dict['app_name']})"
    return model_dicts
