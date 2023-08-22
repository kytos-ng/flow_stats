#########
Changelog
#########
All notable changes to the flow_stats NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====

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

[2023.1.0] - 2023-06-27
***********************

General Information
===================
- ``@rest`` endpoints are now run by ``starlette/uvicorn`` instead of ``flask/werkzeug``.


Deprecated
==========

- After version ``2023.1``, you should migrate to ``kytos_stats``. This is the last major version that ``flow_stats`` will be maintained.


[2022.3.0] - 2023-01-23
***********************

Added
=====

- Added `from_replies_flows` function to map a the replies_flows into generic flows.
- Event ``kytos/of_core.flow_stats.received`` has replaced event ``kytos/of_core.v0x04.messages.in.ofpt_multipart_reply``.
- Added `scripts/kytos_zabbix.py` script to demonstrate how Kytos can be monitored through Zabbix.

Changed
=======

- Update GET ``v1/flow/stats`` endpoint to listing flow stats by dpid.
- v1 is bumped on endpoint routes: GET ``v1/flow/stats``, GET ``v1/packet_count/<flow_id>``, GET ``v1/bytes_count/<flow_id>``, GET ``v1/packet_count/per_flow/<dpid>``, GET ``v1/bytes_count/per_flow/<dpid>``

Removed
=======
- Removed support for OpenFlow 1.0
- `GenericFlow` abstraction
- GET ``flow/match/<dpid>`` endpoint
- GET ``packet_count/sum/{{dpid}}`` endpoint
- GET ``bytes_count/sum/{{dpid}}`` endpoint


[2022.2.1] - 2022-08-15
***********************

Fixed
=====
- Made a shallow copy when iterating on shared data structure to avoid RuntimeError size changed


[2022.2.0] - 2022-08-08
***********************

General Information
===================
- Added unit tests and increased unit test coverage


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
