|Stable| |Tag| |License| |Build| |Coverage| |Quality|

.. raw:: html

  <div align="center">
    <h1><code>amlight/flow_stats</code></h1>

    <strong> Napp responsible for providing flows statistics. </strong>

    <h3><a href="https://kytos-ng.github.io/api/flow_stats.html">OpenAPI Docs</a></h3>
  </div>

  <div align="center">
   <h1><code>flow_stats will be deprecated</code></h1>
  </div>
  <div>
  <a href="https://github.com/kytos-ng/kytos_stats">kytos_stats</a>
   is encouraged to be used instead of this NApp
  </div>

Overview
========
Napp responsible for providing flows statistics.

Installing
========== 

To install this NApp, first, make sure to have the same venv activated as you have ``kytos`` installed on:

.. code:: shell

   $ git clone https://github.com/amlight/flow_stats.git
   $ cd flow_stats
   $ python setup.py develop

Features
========
- REST API to list flows statistics by switch
- REST API to get flows statistics (packet_count and bytes_count) of an specific flow
- REST API to get flows statistics (packet_count and bytes_count) for a switch
- Handle flow stats messages when replies are received

Requirements
============

- `kytos/of_core <https://github.com/kytos-ng/of_core>`

Events
======

Subscribed
----------

- ``kytos/of_core.flow_stats.received``


.. TAGs

.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/amlight/flow_stats
.. |License| image:: https://img.shields.io/github/license/amlight/flow_stats.svg
   :target: https://github.com/amlight/flow_stats/blob/master/LICENSE
.. |Build| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/badges/build.png?b=master
  :alt: Build status
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/?branch=master
.. |Coverage| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/badges/coverage.png?b=master
  :alt: Code coverage
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/?branch=master
.. |Quality| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/badges/quality-score.png?b=master
  :alt: Code-quality score
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_stats/?branch=master
.. |Tag| image:: https://img.shields.io/github/tag/amlight/flow_stats.svg
   :target: https://github.com/kytos-ng/flow_stats/tags



