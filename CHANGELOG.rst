#########
Changelog
#########
All notable changes to the flow_stats NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====

- Added from_replies_flows function in GenericFlow to map FLOW04

Changed
=======

Deprecated
==========

Removed
=======

Fixed
=====

Security
========

[2022.1.0] - 2022-02-08
***********************

Added
=====
- [Issue 12] Enhanced and standardized setup.py `install_requires` to install pinned dependencies
- [Issue 4] Add setup.py and requirements
- [Issue 9] Improve flow_stats handler to avoid reset generic_flows before having all multiple parts

Fixed
=====
- [Issue 13] GET /api/amlight/flow_stats/flow/stats/ not found
- [Issue 8] Fix multipart flow stats reply to avoid data loss and race conditions
- [Issue 5] Removing flow_history from flow_stats as a result of performance issues
