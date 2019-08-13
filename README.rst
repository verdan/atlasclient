=============================
Apache Atlas Client in Python
=============================


.. image:: https://img.shields.io/pypi/v/pyatlasclient.svg
        :target: https://pypi.python.org/pypi/pyatlasclient

.. image:: https://img.shields.io/travis/verdan/pyatlasclient.svg
        :target: https://travis-ci.org/verdan/pyatlasclient

.. image:: https://coveralls.io/repos/github/verdan/pyatlasclient/badge.svg?branch=master
        :target: https://coveralls.io/github/verdan/pyatlasclient?branch=master

.. image:: https://readthedocs.org/projects/pyatlasclient/badge/?version=latest
        :target: https://pyatlasclient.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/verdan/pyatlasclient/shield.svg
     :target: https://pyup.io/repos/github/verdan/pyatlasclient/
     :alt: Updates


Apache Atlas client in Python. Only compatible with Apache Atlas REST API **v2**.

*Based on the awesome work done by Poullet in atlasclient*

* Free software: Apache Software License 2.0
* Documentation: https://pyatlasclient.readthedocs.io.

Get started
-----------

    >>> from atlasclient.client import Atlas
    >>> client = Atlas('<atlas.host>', port=21000, username='admin', password='admin')
    >>> client.entity_guid(<guid>).status
    >>> params = {'typeName': 'DataSet', 'attrName': 'name', 'attrValue': 'data', 'offset': '1', 'limit':'10'}
    >>> search_results = client.search_attribute(**params) 
    >>> for s in search_results:
    ...    for e in s.entities:
    ...         print(e.name)
    ...         print(e.guid)


Features
--------

* Lazy loading: requests are only performed when data are required and not yet available
* Resource object relationships: REST API from sub-resources are done transparently for the user, for instance the user does not have to know that it needs to trigger a different REST request for getting the classifications of a specific entity.  

TODO features  
-------------

* allow multiprocessing

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

