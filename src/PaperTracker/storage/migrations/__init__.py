"""Versioned migration files for PaperTracker's SQLite schema.

Each module in this package must expose a single ``MIGRATION`` constant of
type :class:`~PaperTracker.storage.migration.Migration`.  Modules are
discovered and sorted automatically by
:func:`~PaperTracker.storage.migration._load_migrations`; file names should
follow the ``vNNN_<description>.py`` convention for readability.
"""
