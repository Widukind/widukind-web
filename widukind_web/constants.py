# -*- coding: utf-8 -*-

from dlstats.constants import *

SESSION_LANG_KEY = "current_lang"
SESSION_TIMEZONE_KEY = "current_tz"
SESSION_THEME_KEY = "current_theme"

COL_COUNTERS = "counters"

COL_QUERIES = "queries"

COL_LOGS = "logs"

CHOICES_SORT_DATASETS = (
    ("provider", "provider"),
    ("datasetCode", "dataset"),
    ("name", "serie name"),
    ("lastUpdate", "Last update"),
)

CHOICES_SORT_SERIES = (
    ("startDate", "start date"),
    ("endDate", "end date"),
    ("provider", "provider"),
    ("datasetCode", "dataset"),
    ("name", "serie name"),
    ("key", "serie key"),
)

