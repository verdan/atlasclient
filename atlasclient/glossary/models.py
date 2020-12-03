import logging

from atlasclient import base, events
from atlasclient.data_types import AtlasRelatedCategoryHeader, AtlasRelatedTermHeader, AtlasRelatedObjectId
from atlasclient.events import keep_path_and_url
from atlasclient.glossary.data_types import (AtlasGlossary, AtlasGlossaryCategory,
                                             AtlasGlossaryTerm, AtlasGlossaryExtInfo)

LOG = logging.getLogger('pyatlasclient')

BASE_URL_GLOSSARY = "glossary"


class GlossaryCollection(base.QueryableModelCollection):
    @events.evented
    @keep_path_and_url
    def fetch_categories(self, glossary_guid):
        """
        GET /v2/glossary/{glossaryGuid}/categories: Get the categories belonging to a specific glossary
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/{glossary_guid}/categories'
        self.model_class.data_class = AtlasGlossaryCategory
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def fetch_categories_headers(self, glossary_guid):
        """
        GET /v2/glossary/{glossaryGuid}/categories/headers: Get the categories headers belonging to a specific glossary
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/{glossary_guid}/categories/headers'
        self.model_class.data_class = AtlasRelatedCategoryHeader
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def fetch_terms(self, glossary_guid):
        """
        GET /v2/glossary/{glossaryGuid}/terms: Get terms belonging to a specific glossary
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/{glossary_guid}/terms'
        self.model_class.data_class = AtlasGlossaryTerm
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def fetch_terms_headers(self, glossary_guid):
        """
        GET /v2/glossary/{glossaryGuid}/terms/headers: Get the terms headers belonging to a specific glossary
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/{glossary_guid}/terms/headers'
        self.model_class.data_class = AtlasRelatedTermHeader
        self.inflate()
        return self


class Glossary(base.QueryableModelV2):
    """
    GET /v2/glossary: Retrieve all glossaries registered with Atlas
    POST /v2/glossary: Create a glossary

    GET /v2/glossary/{glossaryGuid}: Get a specific Glossary
    PUT /v2/glossary/{glossaryGuid}: Update the given glossary
    DELETE /v2/glossary/{glossaryGuid}: Delete a glossary
    """
    collection_class = GlossaryCollection
    data_class = AtlasGlossary
    path = BASE_URL_GLOSSARY
    primary_key = 'guid'

    @events.evented
    @keep_path_and_url
    def detailed(self):
        """
        GET /v2/glossary/{glossaryGuid}/detailed: Get a specific Glossary
        """
        self.url = f'{self.parent.url}/{self.primary_key_value}/detailed'
        self.data_class = AtlasGlossaryExtInfo
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def partial_update(self, **kwargs):
        """
        PUT /v2/glossary/{glossaryGuid}/partial: Partially update the glossary
        """
        self.url = f'{self.parent.url}/{self.primary_key_value}/partial'
        return super(Glossary, self).partial_update(**kwargs)


class GlossaryCategoryCollection(base.QueryableModelCollection):
    @events.evented
    @keep_path_and_url
    def fetch_related(self, category_guid):
        """
        GET /v2/glossary/category/{categoryGuid}/related: Get all related categories (parent and children)
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/category/{category_guid}/related'
        self.model_class.data_class = AtlasRelatedCategoryHeader
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def fetch_terms(self, category_guid):
        """
        GET /v2/glossary/category/{categoryGuid}/terms: Get all terms associated with the specific category
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/category/{category_guid}/terms'
        self.model_class.data_class = AtlasRelatedTermHeader
        self.inflate()
        return self


class GlossaryCategory(base.QueryableModelV2):
    """
    POST /v2/glossary/category: Create a single glossary category
    GET /v2/glossary/category/{categoryGuid}: Get specific glossary category
    DELETE /v2/glossary/category/{categoryGuid}: Delete a glossary category
    PUT /v2/glossary/category/{categoryGuid}: Update the given glossary category
    """
    collection_class = GlossaryCategoryCollection
    data_class = AtlasGlossaryCategory
    path = f'{BASE_URL_GLOSSARY}/category'
    primary_key = 'guid'

    @events.evented
    @keep_path_and_url
    def partial_update(self, **kwargs):
        """
        PUT /v2/glossary/category/{categoryGuid}/partial: Partially update the glossary category
        """
        self.url = f'{self.parent.url}/{self.primary_key_value}/partial'
        return super(GlossaryCategory, self).partial_update(**kwargs)


class GlossaryCategories(base.QueryableModelV2):
    """
    POST /v2/glossary/categories: Create glossary categories in bulk
    A category must be anchored to a Glossary at the time of creation
    """
    collection_class = base.QueryableModelCollectionBulk
    data_class = AtlasGlossaryCategory
    path = f'{BASE_URL_GLOSSARY}/categories'


class GlossaryTermCollection(base.QueryableModelCollection):
    @events.evented
    @keep_path_and_url
    def fetch_related(self, term_guid):
        """
        GET /v2/glossary/terms/{termGuid}/related: Get all related terms for a specific term
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/terms/{term_guid}/related'
        self.model_class.data_class = AtlasRelatedTermHeader
        self.inflate()
        return self


class GlossaryTerm(base.QueryableModelV2):
    """
    Glossary term definition, a term must be anchored to a Glossary
    at the time of creation optionally it can be categorized as well

    POST /v2/glossary/term: Create a glossary term
    DELETE /v2/glossary/term/{termGuid}: Delete a glossary term
    GET /v2/glossary/term/{termGuid}: Get specific glossary term
    PUT /v2/glossary/term/{termGuid}: Update the given glossary term
    """
    collection_class = GlossaryTermCollection
    data_class = AtlasGlossaryTerm
    path = f'{BASE_URL_GLOSSARY}/term'
    primary_key = 'guid'

    @events.evented
    @keep_path_and_url
    def partial_update(self, **kwargs):
        """
        PUT /v2/glossary/term/{termGuid}/partial: Partially update the glossary term
        """
        self.url = f'{self.parent.url}/{self.primary_key_value}/partial'
        return super(GlossaryTerm, self).partial_update(**kwargs)


class GlossaryTermsCollection(base.QueryableModelCollectionBulk):

    @events.evented
    @keep_path_and_url
    def fetch_assigned_entities(self, term_guid):
        """
        GET /v2/glossary/terms/{termGuid}/assignedEntities: Get all entity headers assigned with the specified term
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/terms/{term_guid}/assignedEntities'
        self.model_class.data_class = AtlasRelatedObjectId
        self.inflate()
        return self

    @events.evented
    @keep_path_and_url
    def assign_entities(self, term_guid, data):
        """
        POST /v2/glossary/terms/{termGuid}/assignedEntities: Assign the given term to the provided list of entity headers
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/terms/{term_guid}/assignedEntities'
        self.model_class.data_class = AtlasRelatedObjectId
        return self.create(data)

    @events.evented
    @keep_path_and_url
    def delete_assigned_entities(self, term_guid, data):
        """
        DELETE /v2/glossary/terms/{termGuid}/assignedEntities: Remove the term assignment for the given list of entity headers
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/terms/{term_guid}/assignedEntities'
        self.model_class.data_class = AtlasRelatedObjectId
        return self.delete(data=data)

    @events.evented
    @keep_path_and_url
    def update_assigned_entities(self, term_guid, data):
        """
        PUT /v2/glossary/terms/{termGuid}/assignedEntities: Updates the term assignment for the given list of entity headers
        """
        self.model_class.path = f'{BASE_URL_GLOSSARY}/terms/{term_guid}/assignedEntities'
        self.model_class.data_class = AtlasRelatedObjectId
        return self.update(data=data)


class GlossaryTerms(base.QueryableModelV2):
    """
    POST /v2/glossary/terms: Create glossary terms in bulk
    Glossary term definition, a term must be anchored to a Glossary
    at the time of creation optionally it can be categorized as well
    """
    collection_class = GlossaryTermsCollection
    data_class = AtlasGlossaryTerm
    path = f'{BASE_URL_GLOSSARY}/terms'
