# -*- coding: utf-8 -*-

from widukind_common.constants import *

SESSION_LANG_KEY = "current_lang"
SESSION_TIMEZONE_KEY = "current_tz"
SESSION_THEME_KEY = "current_theme"

COL_SESSION = "session_web"
COL_ALL.append(COL_SESSION)

CHOICES_SORT_DATASETS = (
    ('provider_name', 'Provider Name'),
    ("dataset_code", "Dataset Code"),
    ("name", "Dataset Name"),
    ("last_update", "Last update"),
)

CHOICES_SORT_SERIES = (
    ("start_date", "Start Date"),
    ("end_date", "End Date"),
    ('provider_name', 'Provider Name'),
    ("dataset_code", "Dataset Code"),
    ("name", "Series Name"),
    ("key", "Series Key"),
)

