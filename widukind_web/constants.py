# -*- coding: utf-8 -*-

from widukind_common.constants import *

SESSION_LANG_KEY = "current_lang"
SESSION_TIMEZONE_KEY = "current_tz"
SESSION_THEME_KEY = "current_theme"

CHOICES_SORT_DATASETS = (
    ("provider", "provider"),
    ("datasetCode", "dataset"),
    ("name", "serie name"),
    ("last_update", "Last update"),
)

CHOICES_SORT_SERIES = (
    ("startDate", "start date"),
    ("endDate", "end date"),
    ("provider", "provider"),
    ("datasetCode", "dataset"),
    ("name", "serie name"),
    ("key", "serie key"),
)

