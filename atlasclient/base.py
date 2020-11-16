#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Defines all the base classes for response objects.
"""

import ast
import json
import logging

import six
import time
from datetime import datetime, timedelta

from atlasclient import events, exceptions, utils
from atlasclient.exceptions import BadRequest

LOG = logging.getLogger('pyatlasclient')

OLDEST_SUPPORTED_VERSION = (1, 7, 0)


class PollableMixin(object):
    """A mixin class that allows for polling for status updates automatically.

    It modifies the behavior of the wait() method to poll the Atlas API until
    a certain precondition is met.  That precondition is defined by the
    is_finished property which must be defined by the subclass that mixes this
    one in.

    You can also set default_interval on the subclass to define the polling
    interval, and default_timeout to define the amount of time before it will
    give up.
    """
    default_interval = 15
    default_timeout = 3600

    @property
    def has_failed(self):
        raise NotImplementedError("'has_failed' must be defined by subclasses")

    @property
    def is_finished(self):
        raise NotImplementedError("'is_finished' must be defined by subclasses")

    @events.evented
    def wait(self, interval=None, timeout=None):
        if not interval:
            interval = self.default_interval
        if not timeout:
            timeout = self.default_timeout

        end = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() < end:
            if self.has_failed:
                raise exceptions.Failed(model=self)
            elif self.is_finished:
                return self
            else:
                events.publish(self, 'wait', events.states.PROGRESS)
                time.sleep(interval)
                self.refresh()

        raise exceptions.Timeout(timeout, "Long-running task failed to complete")


class GeneratedIdentifierMixin(object):
    @property
    def identifier(self):
        """These models have server-generated identifiers.

        If we don't already have it in memory, then assume that it has not
        yet been generated.
        """
        if self.primary_key not in self._data:
            return 'Unknown'
        return str(self._data[self.primary_key])


class ModelCollection(object):
    """A collection of Atlas model objects.

    This collection can be empty, in the which case it will load the appropriate
    data on demand, if it can. This class serves as a common base class for
    collections of two types of objects, QueryableModel and DependentModel.  The
    differences between those are explained in more detail below.

    These collections are iterable, so you can do things like:

    for model in collection:
        model.do_something()

    They are also callable as methods, which lets you filter the collection to
    a subset, as such:

    model = collection(model_id)
    for model in collection([model_id, model_id]):
        model.do_something()

    for model in collection(model_id, model_id):
        model.do_something()

    for model in collection([model_dict, model_dict]):
        model.do_something()

    This is what enables things like:

    entity_bulk_collection = atlas_client.entity_bulk(**params)
    for bulk in entity_bulk_collection:
        for entity in bulk.entities:
            entity.version == 12345

    """

    def __init__(self, client, model_class, parent=None):
        self.client = client
        self.model_class = model_class
        self.parent = parent
        self._is_inflated = False
        self._models = []
        self._iter_marker = 0

    def __iter__(self):
        self.inflate()
        self._iter_marker = 0
        return self

    def next(self):
        self.inflate()
        if self._iter_marker >= len(self._models):
            raise StopIteration
        model = self._models[self._iter_marker]
        self._iter_marker += 1
        return model

    def __next__(self):
        return self.next()

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("'__call__' must be defined by subclasses")

    def inflate(self):
        raise NotImplementedError("'inflate' must be defined by subclasses")

    def refresh(self):
        self._is_inflated = False
        return self.inflate()

    def remove(self, model):
        self._models = [x for x in self._models if x.identifier != model.identifier]
        return

    @events.evented
    def wait(self, **kwargs):  # pylint: disable=unused-argument
        """Wait until the collection is loaded."""
        return self.inflate()

    def to_dict(self):
        self.inflate()
        return [x.to_dict() for x in self._models]


class QueryableModelCollection(ModelCollection):
    """A collection of QueryableModel objects.

    These collections are backed by a url that can be used to load and/or
    reload the collection from the server.  For the most part, they are
    lazy-loaded on demand when you attempt to access members of the collection,
    but they can be preloaded with data by passing in a list of dictionaries.
    This comes in handy because the Atlas API often returns related objects
    when you do a GET call on a specific resource.  So for example:
    """

    def __init__(self, *args, **kwargs):
        super(QueryableModelCollection, self).__init__(*args, **kwargs)
        self.request = None
        self._filter = {}

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            if isinstance(args[0], list):
                # allow for passing in a list of ids and filtering the set
                items = args[0]
            else:
                identifier = str(args[0])
                return self.model_class(self, href='/'.join([self.url, identifier]),
                                        data={self.model_class.primary_key: identifier})
        else:
            items = args

        if items:
            self._models = []
            self._is_inflated = True
            for item in items:
                if isinstance(item, dict):
                    # we're preloading this object from existing response data
                    model = self.model_class(self,
                                             href=item['href'].replace('classifications/', 'classification/'))
                    model.load(item)
                else:
                    # we only have the primary id, so create an deflated model
                    model = self.model_class(self,
                                             href='/'.join([self.url, item]).replace('classifications/',
                                                                                     'classification/'),
                                             data={self.model_class.primary_key: item})
                self._models.append(model)
            return self
        self._is_inflated = False
        self._filter = {}
        self._models = []
        if kwargs:
            prefix = self.model_class.data_key
            for (key, value) in kwargs.items():
                if self.model_class.use_key_prefix:
                    key = '/'.join([prefix, key])
                if not isinstance(value, six.string_types):
                    value = json.dumps(value)
                self._filter[key] = value

        return self

    @property
    def is_admin_api(self):
        return False

    @property
    def url(self):
        """The url for this collection."""
        if self.is_admin_api:
            pieces = [self.client.base_url, 'api', 'atlas', 'admin']
        elif self.parent is None:
            # TODO: differing API Versions?
            pieces = [self.client.base_url, 'api', 'atlas', 'v2']
        else:
            pieces = [self.parent.url]

        pieces.append(self.model_class.path)
        return '/'.join(pieces)

    def inflate(self):
        """Load the collection from the server, if necessary."""
        if not self._is_inflated:
            self.check_version()
            for k, v in self._filter.items():
                if '[' in v:
                    try:
                        self._filter[k] = ast.literal_eval(v)
                    except SyntaxError:
                        # In case of DSL Queries, we can specify the list in a query
                        # but this will try to evaluate this as a list and failed as syntax error.
                        self._filter[k] = v
            LOG.debug("Trying to fetch collection from server - ".format(self.model_class.__class__.__name__))
            self.load(self.client.get(self.url, params=self._filter))

        self._is_inflated = True
        return self

    @events.evented
    def load(self, response):
        """Parse the GET response for the collection.

        This operates as a lazy-loader, meaning that the data are only downloaded
        from the server if there are not already loaded.
        Collection items are loaded sequentially.

        In some rare cases, a collection can have an asynchronous request
        triggered.  For those cases, we handle it here.
        """
        LOG.debug("Parsing the GET response for the collection - {}".format(self.model_class.__class__.__name__))
        self._models = []
        if isinstance(response, dict):
            for key in response.keys():
                model = self.model_class(self, href='')
                model.load(response[key])
                self._models.append(model)
        else:
            for item in response:
                model = self.model_class(self,
                                         href=item.get('href'))
                model.load(item)
                self._models.append(model)

    def create(self, *args, **kwargs):
        """Add a resource to this collection."""
        LOG.debug(f"Adding a new resource to the collection {self.__class__.__name__} with the data {kwargs}")
        href = self.url
        if len(args) == 1:
            kwargs[self.model_class.primary_key] = args[0]
            href = '/'.join([href, args[0]])
        model = self.model_class(self,
                                 href=href.replace('classifications/', 'classification/'),
                                 data=kwargs)
        model.create(**kwargs)
        self._models.append(model)
        return model

    def update(self, **kwargs):
        """Update all resources in this collection."""
        LOG.debug(f"Updating all resources in the collection "
                  f"{self.model_class.__class__.__name__} "
                  f"with the following arguments {kwargs}")
        self.inflate()
        for model in self._models:
            model.update(**kwargs)
        return self

    def delete(self, **kwargs):
        """Delete all resources in this collection."""
        LOG.debug("Deleting all resources in this collection:  ".format(self.model_class.__class__.__name__))
        self.inflate()
        for model in self._models:
            model.delete(**kwargs)
        return

    @events.evented
    def wait(self, **kwargs):
        """Wait until any pending asynchronous requests are finished for this collection."""
        if self.request:
            self.request.wait(**kwargs)
            self.request = None
        return self.inflate()

    def check_version(self):
        if (
                self.model_class.min_version > OLDEST_SUPPORTED_VERSION and self.client.version < self.model_class.min_version):
            min_version = utils.version_str(self.model_class.min_version)
            curr_version = utils.version_str(self.client.version)
            raise exceptions.ClientError(message="Cannot access %s in version %s, it was added in "
                                                 "version %s" % (self.url, curr_version,
                                                                 min_version))


class DependentModelCollection(ModelCollection):
    """A collection of DependentModel objects.

    Since these are always preloaded by parent objects, we just need to instantiate
    the model objects when a collection is called with a list of dictionaries
    provided by another API response.  There's no lazy-loading here and no way
    to regenerate the collection other than refreshing the parent object.
    """

    def __call__(self, *args):
        """Generate the models for this collection.

        Since these models aren't backed by URLs, any information they contain
        should have been included in the parent's response.  This makes it easy
        to generate the list of model objects with that data, as such:

            parent.collection_name(dict1, dict2, dict3,...)
        -or-
            parent.collection_name([dict1, dict2, dict3,...])

        Unlike QueryableModelCollection objects, there is no lazy-loading here.
        What you start with is all you ever get.  If the parent resource is
        reloaded, it should create new collections for these resources.
        """
        LOG.debug("Generating the models for this collection:  ".format(self.model_class.__class__.__name__))
        items = []
        if len(args) == 1:
            if isinstance(args[0], list):
                items = args[0]
            else:
                matches = [x for x in self._models if x.identifier == args[0]]
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    error_message = "More than one {0} with {1} '{2}' found in collection" \
                        .format(self.model_class.__class__.__name__,
                                self.model_class.primary_key, args[0])
                    LOG.error(error_message)
                    raise ValueError(error_message)
                return None

        if len(items) > 0:
            self._models = []
            for item in items:
                model = self.model_class(self, data=item)
                self._models.append(model)

        return self

    def inflate(self):
        self._is_inflated = True
        return self

    def __len__(self):
        if self._is_inflated:
            return len(self._models)
        else:
            self.inflate()
            return len(self._models)


class Model(object):
    """An Atlas model represents a resource in the Atlas API.

    This is the base class with common functionality between objects that are
    backed by URLs on the Atlas server (QueryableModel) and those that are
    just metadata objects returned by other API calls (DependentModel).

    All of the field names defined in the 'fields' list are retrievable via
    attributes.  These are readonly at the moment. There is no way to modify
    the values once set, although that behavior differs for some subclasses.

    'relationships' defines a map between attribute names and the model class
    that should be associated with their collections.  So for example:

    relationships = {
        'entities': Entity
    }

    model.entity will return a ModelCollection of Entity objects.

    """
    primary_key = None
    fields = []
    relationships = {}
    min_version = OLDEST_SUPPORTED_VERSION

    def __init__(self, parent, data=None):
        LOG.debug("Generating new model class: {} with the data: {}".format(self.__class__.__name__, data))
        if data is None:
            data = {}

        self._data = dict((key, value) for key, value in six.iteritems(data)
                          if key in set(self.fields))
        self.parent = parent
        self.client = parent.client
        self._is_inflated = False
        self._relationship_cache = {}

    def __dir__(self):
        fields_dict = dict()
        for field in self.fields:
            fields_dict[field] = field
        d1 = {}
        for item in [self.__dict__, fields_dict, self.relationships]:
            d1.update(item)
        return d1.keys()

    @property
    def identifier(self):
        """A model's identifier is the value of its primary key."""
        if self.primary_key is None:
            return None

        if self.primary_key not in self._data:
            self.inflate()
        return str(self._data[self.primary_key])

    def __getattr__(self, attr):
        """Lazy-load related objects or object data.

        Any fields in self.fields or relationship names in self.relationships
        can be accessed as attributes on the object.  They will only load data
        if it can't reasonably be derived from already-loaded information.  i.e.
        they won't do an http request unless they have to.
        """
        if attr in self.relationships:
            rel_class = self.relationships[attr]
            # we can't lazy-load DependentModel types
            if issubclass(rel_class, DependentModel):
                rel_class(parent=self).inflate()

            if attr not in self._relationship_cache:
                self._relationship_cache[attr] = rel_class.collection_class(
                    self.client, rel_class,
                    parent=self,
                )
            return self._relationship_cache[attr]

        if attr in self.fields:
            # if it came from a parent inflation, we might only have partial data
            if attr not in self._data:
                LOG.debug(f"Lazy-loading the relationship attribute: '{attr}'.")
                self.inflate()
            return self._data.get(attr)

        LOG.error("Missing attr %s: %s", self.__class__.__name__, attr)

        raise AttributeError(attr)

    def refresh(self):
        """Reload a model from its data source."""
        self._is_inflated = False
        return self.inflate()

    def inflate(self):
        """Inflate a model by loading it's data from whatever backend it uses.

        Any methods that need access to information that doesn't yet exist will
        lazy-load their data using this method.  Subclasses should implement
        this method for their particular type of data.
        """
        raise NotImplementedError("'inflate' must be defined by subclasses")

    def to_dict(self):
        """Convert a model to a dictionary."""
        self.inflate()
        return self._data

    # TODO: this is only being used in one place so far, maybe nix it?
    def to_json_dict(self):
        """Convert the object to a dictionary for JSON serialization.

        This is most commonly used when passing objects from one API call into
        the create method on another object.  Rather than having to manually
        convert to the appropriate dictionary value, this method will implicitly
        do it for you.  If your Model requires anything other than the default
        of { primary_key: id }, then you can overload it and do what is needed.
        """
        return {self.primary_key: self.identifier}

    @events.evented
    def wait(self, **kwargs):  # pylint: disable=unused-argument
        """Calling wait() on a model makes it wait until the object is in a valid state.

        So, for example, if you wait() on a cluster after creating it, it will
        not return until that cluster is activated and running.  In some cases,
        it will just immediately return because the resource is already in the
        desired state.  This method is intended to be overloaded by models that
        define 'ready' in a different way, but the default behavior is to just
        delegate to the 'inflate' method on the object for objects that don't
        require any additional effort.
        """
        return self.inflate()


class DependentModel(Model):
    """A dependent model is model that is not accessible directly via a URL.

    Many Atlas objects have related data that is just returned by the API
    but not directly accessible via a specific URL other than that of the parent
    object.  This class attempts to make those objects generally interchangeable
    with models that are backed by URLs.
    """

    collection_class = DependentModelCollection

    def inflate(self):
        self._is_inflated = True
        return self


class QueryableModel(Model):
    """A queryable model is a model that is backed by a URL.

    Most resources in the Atlas API are directly accessible via a URL, and this
    class serves as a base class for all of them.

    There are some nice convenience methods like create(), update(), and
    delete().  Unlike some ORMs, there's no way to modify values by updating
    attributes directly and then calling save() or something to send those to
    the server.  You must call update() with the keyword arguments of the fields
    you wish to update.  I've always found that allowing for attribute updates
    is problematic as some users expect that the update will happen immediately,
    when in reality they still have to call another method like save() to make
    those changes permanent. I might recant if enough people request the addition
    of attribute setters.

    All of the data in these objects is lazy-loaded.  It will only do the API
    request at a point where it needs to in order to proceed.  These cases are:

        * accessing an attribute that isn't already loaded
        * accessing a relationship
        * calling 'inflate()' directly
        * calling wait()

    If you hit a situation where you want to force an already-loaded object to
    get the latest data from the server, the refresh() method will do that for
    you.
    """
    collection_class = QueryableModelCollection
    use_key_prefix = False
    path = None
    data_key = None
    relationships = {}
    method = "get"  # To keep track of the method type of each request
    _url = None     # This is to handle the getter/setter of the property

    def __init__(self, *args, **kwargs):
        self.request = None
        if 'href' in kwargs:
            self._href = kwargs.pop('href')
            if self._href is not None:
                self._href = self._href.replace('classifications/', 'classification/')
        else:
            self._href = None
        self._is_inflated = False
        self._is_inflating = False
        super(QueryableModel, self).__init__(*args, **kwargs)

    @property
    def url(self):
        """Gets the url for the resource this model represents.

        It will just use the 'href' passed in to the constructor if that exists.
        Otherwise, it will generated it based on the collection's url and the
        model's identifier.
        """
        if self._url:
            return self._url

        _url = None
        if self._href is not None:
            _url = self._href
        elif self.identifier:
            #  for some reason atlas does not use classifications here in the path when considering one classification
            _url = '/'.join([self.parent.url.replace('classifications/', 'classficiation/'), self.identifier])
        if _url:
            self.url = _url
            return self._url
        raise exceptions.ClientError("Not able to determine object URL")

    @url.setter
    def url(self, value):
        self._url = value

    def inflate(self, url=None):
        """Load the resource from the server, if not already loaded."""
        if not self._is_inflated:
            if self._is_inflating:
                #  catch infinite recursion when attempting to inflate
                #  an object that doesn't have enough data to inflate
                msg = ("There is not enough data to inflate this object.  "
                       "Need either an href: {} or a {}: {}")
                msg = msg.format(self._href, self.primary_key, self._data.get(self.primary_key))
                LOG.error(msg)
                raise exceptions.ClientError(msg)

            self._is_inflating = True

            try:
                params = self.searchParameters if hasattr(self, 'searchParameters') else {}
                # To keep the method same as the original request. The default is GET
                self.load(self.client.request(self.method, url or self.url, **params))
            except Exception:
                self.load(self._data)

            self._is_inflated = True
            self._is_inflating = False
        return self

    def _generate_input_dict(self, **kwargs):
        if self.data_key:
            data = {self.data_key: {}}
            if len(kwargs) == 0:
                data = self._data
                LOG.info(f"Input data generated: {data}")
                return data
            for field in kwargs:
                if field in self.fields:
                    data[self.data_key][field] = kwargs[field]
                else:
                    data[field] = kwargs[field]
            LOG.info(f"Input data generated: {data}")
            return data
        else:
            LOG.info(f"No data key specified - Using kwargs: {kwargs}")
            return kwargs

    @events.evented
    def load(self, response):
        """The load method parses the raw JSON response from the server.

        Most models are not returned in the main response body, but in a key
        such as 'entity', defined by the 'data_key' attribute on the class.
        Also, related objects are often returned and can be used to pre-cache
        related model objects without having to contact the server again.  This
        method handles all of those cases.

        Also, if a request has triggered a background operation, the request
        details are returned in a 'Requests' section. We need to store that
        request object so we can poll it until completion.
        """
        if 'href' in response:
            self._href = response.pop('href')
        if self.data_key and self.data_key in response:
            self._data.update(response.pop(self.data_key))
            #  preload related object collections, if received
            for rel in [x for x in self.relationships if x in response and response[x]]:
                rel_class = self.relationships[rel]
                collection = rel_class.collection_class(
                    self.client, rel_class, parent=self
                )
                self._relationship_cache[rel] = collection(response[rel])
        else:
            self._data.update(response)

    @events.evented
    def create(self, **kwargs):
        """Create a new instance of this resource type.

        As a general rule, the identifier should have been provided, but in
        some subclasses the identifier is server-side-generated.  Those classes
        have to overload this method to deal with that scenario.
        """
        self.method = 'post'
        if self.primary_key in kwargs:
            del kwargs[self.primary_key]
        data = self._generate_input_dict(**kwargs)
        LOG.info(f"Creating a new instance of the resource "
                 f"{self.__class__.__name__}, with data: {data}")
        self.load(self.client.post(self.url, data=data))
        return self

    @events.evented
    def update(self, **kwargs):
        """Update a resource by passing in modifications via keyword arguments.

        For example:

            model.update(a='b', b='c')

        is generally converted to:

            PUT model.url { model.data_key: {'a': 'b', 'b': 'c' } }

        If the request body doesn't follow that pattern, you'll need to overload
        this method to handle your particular case.
        """
        self.method = 'put'
        data = self._generate_input_dict(**kwargs)
        LOG.info(f"Updating an instance of the resource "
                 f"{self.__class__.__name__}, with data: {data}")
        self.load(self.client.put(self.url, data=data))
        return self

    @events.evented
    def delete(self, **kwargs):
        """Delete a resource by issuing a DELETE http request against it."""
        self.method = 'delete'
        if len(kwargs) > 0:
            self.load(self.client.delete(self.url, params=kwargs))
        else:
            self.load(self.client.delete(self.url))
        LOG.info(f"Deleting the resource {self.__class__.__name__} using url: {self.url}")
        self.parent.remove(self)
        return

    @events.evented
    def wait(self, **kwargs):
        """Wait until any pending asynchronous requests are finished."""
        if self.request:
            self.request.wait(**kwargs)
            self.request = None
        return self.inflate()

    def entities_with_relationships(self, attributes=None):
        """
        In some cases Atlas does not provide the relationship attributes in
        referredEntities dictionary. To handle all those corner cases (like searching
        on the parent type etc. this function verifies if attribute is under referredEntities,
        otherwise fetch it and store it for further use.
        :param attributes: A list of relationship attributes.
        :return: A list of entities, with detailed relationship attributes.
        """

        def _fix_relationships(client, entities, ref_entities, attrs):
            rel_attribute_ids = set()
            for entity in entities:
                relationship_attrs = entity.relationshipAttributes

                # Only fix the attributes if specified in parameter, else fix all.
                attrs = attrs or relationship_attrs.keys()

                for attribute in attrs:
                    rel_attr = relationship_attrs.get(attribute)
                    if isinstance(rel_attr, list):
                        for index, item in enumerate(rel_attr):
                            guid = item.guid if hasattr(item, 'guid') else item.get('guid')
                            # A check to be on the safe side / and for test cases
                            if guid:
                                if guid in ref_entities:
                                    entity.relationshipAttributes[attribute][index] = ref_entities[guid]
                                else:
                                    rel_attribute_ids.add(guid)
                    if isinstance(rel_attr, dict):
                        guid = rel_attr.get('guid')
                        # A check to be on the safe side / and for test cases
                        if guid:
                            if guid in ref_entities:
                                entity.relationshipAttributes[attribute] = ref_entities[guid]
                            else:
                                rel_attribute_ids.add(guid)

            if rel_attribute_ids:
                _rel_attr_collection = client.entity_bulk(guid=list(rel_attribute_ids))
                # noinspection PyTypeChecker
                for rel_entities in _rel_attr_collection:
                    ref_entities.update(dict((rel_entity.guid, rel_entity._data)
                                             for rel_entity in rel_entities.entities))

                    # Fix remaining entities recursively
                    entities = _fix_relationships(client, entities, ref_entities, attrs)

            return entities

        if self.entities and isinstance(self.entities, DependentModelCollection):
            referred_entities = self.referredEntities or dict()
            return _fix_relationships(self.client, self.entities, referred_entities, attributes)


class QueryableModelCollectionBulk(QueryableModelCollection):
    def create(self, data):
        """
        Create entities in bulk amount. Data must be a list of instances
        """
        LOG.debug(f"Trying to create {self.__class__.__name__} with the data {data}")
        if not isinstance(data, list):
            raise BadRequest(
                url=self.model_class.path,
                method="POST",
                message=f'Data should be a list of "{self.model_class.data_class}"'
            )
        _data = list()
        for item in data:
            # noinspection PyProtectedMember
            _data.append(
                self.model_class.data_class(**item).to_dict(
                    data_key=self.model_class.data_key,
                    ignore_falsy=True)
            )

        self.load(self.client.post(self.url, data=_data))
        return self._models

    def delete(self, data):
        """
        Deletes entities in bulk amount. Data must be a list of instances
        """
        LOG.debug(f"Trying to delete {self.__class__.__name__} with the data {data}")
        if not isinstance(data, list):
            raise BadRequest(
                url=self.model_class.path,
                method="DELETE",
                message=f'Data should be a list of "{self.model_class.data_class}"'
            )
        _data = list()
        for item in data:
            # noinspection PyProtectedMember
            _data.append(
                self.model_class.data_class(**item).to_dict(
                    data_key=self.model_class.data_key,
                    ignore_falsy=True)
            )

        self.load(self.client.delete(self.url, data=_data))
        return self._models

    def update(self, data):
        """
        Updates entities in bulk amount. Data must be a list of instances
        """
        LOG.debug(f"Trying to update {self.__class__.__name__} with the data {data}")
        if not isinstance(data, list):
            raise BadRequest(
                url=self.model_class.path,
                method="PUT",
                message=f'Data should be a list of "{self.model_class.data_class}"'
            )
        _data = list()
        for item in data:
            # noinspection PyProtectedMember
            _data.append(
                self.model_class.data_class(**item).to_dict(
                    data_key=self.model_class.data_key,
                    ignore_falsy=True)
            )

        self.load(self.client.put(self.url, data=_data))
        return self._models


class QueryableModelV2(QueryableModel):
    """
    Leverages the support of Python's Data Classes for the implementation.
    """
    data_class = None
    data_class_data = None
    primary_identifier = None

    def __init__(self, *args, **kwargs):
        self.primary_key_value = kwargs.get("data", {}).get(self.primary_key)
        super(QueryableModelV2, self).__init__(*args, **kwargs)

    def __dir__(self):
        attributes = list()
        for item in self.data_class.__mro__:
            if item.__name__ != 'object':
                attributes.extend(list(item.__dataclass_fields__.keys()))
        return attributes

    def __getattr__(self, attr):
        """Lazy-load related objects or object data.
        """
        try:
            return getattr(self.data_class_data, attr)
        except AttributeError:
            if hasattr(self.data_class, attr):
                # To keep the method same as the original request. The default is GET
                self.load(self.client.request("get", self.url))
                return getattr(self.data_class_data, attr)
            else:
                return super(QueryableModelV2, self).__getattr__(attr)
        except Exception as ex:
            raise ex


    def to_dict(self):
        """Convert a model to a dictionary."""
        if not self.data_class_data:
            self._is_inflated = False
            self.inflate()
        return self.data_class_data.to_dict()

    def _generate_input_dict(self, **kwargs):
        if len(kwargs):
            return self.data_class(**kwargs).to_dict(data_key=self.data_key, ignore_falsy=True)
        else:
            return self.to_dict()

    @events.evented
    def update(self, **kwargs):
        """Update a resource by passing in modifications via keyword arguments.

        For example:

            model.update(a='b', b='c')

        If the request body doesn't follow that pattern, you'll need to overload
        this method to handle your particular case.
        """
        data = self.to_dict()
        data.update(kwargs)
        self.method = 'put'
        self.load(self.client.put(self.url, data=data))
        return self

    @events.evented
    def partial_update(self, **kwargs):
        """
        Partially Update a resource by passing in modifications via keyword arguments.
        """
        self.method = 'put'
        self.load(self.client.put(self.url, data=kwargs))
        return self

    @events.evented
    def load(self, response):
        if 'href' in response:
            self._href = response.pop('href')
        self.data_class_data = self.data_class(**response)


