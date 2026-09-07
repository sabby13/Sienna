"""Persistence: SQLite is the single source of truth.

db.py centralizes connection creation so the mandatory PRAGMAs (foreign_keys=ON,
WAL, busy_timeout) can never be skipped. M0 has only the app_meta table.
"""
