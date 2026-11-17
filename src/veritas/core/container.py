from typing import Optional
from veritas.core.interfaces import (
    ISearchProvider,
    IContentFetcher,
    ICredibilityEvaluator,
    ILedgerRepository,
    IGraphRepository,
    IImageForensicsService,
    IReverseImageProvider,
    IVideoForensicsService,
    IClaimDedupService
)

class DependencyContainer:
    """Central service registry and dependency injection container (SOLID - Dependency Inversion)."""

    def __init__(self):
        self._search_provider: Optional[ISearchProvider] = None
        self._content_fetcher: Optional[IContentFetcher] = None
        self._credibility_evaluator: Optional[ICredibilityEvaluator] = None
        self._ledger_repository: Optional[ILedgerRepository] = None
        self._graph_repository: Optional[IGraphRepository] = None
        self._image_forensics_service: Optional[IImageForensicsService] = None
        self._reverse_image_provider: Optional[IReverseImageProvider] = None
        self._video_forensics_service: Optional[IVideoForensicsService] = None
        self._claim_dedup_service: Optional[IClaimDedupService] = None

    def get_search_provider(self) -> ISearchProvider:
        if self._search_provider is None:
            from veritas.services.search_service import HybridSearchProvider
            self._search_provider = HybridSearchProvider()
        return self._search_provider

    def set_search_provider(self, provider: ISearchProvider):
        """Allows substituting search provider (Liskov Substitution / Open-Closed)."""
        self._search_provider = provider

    def get_content_fetcher(self) -> IContentFetcher:
        if self._content_fetcher is None:
            from veritas.services.fetcher_service import HtmlContentFetcher
            self._content_fetcher = HtmlContentFetcher()
        return self._content_fetcher

    def set_content_fetcher(self, fetcher: IContentFetcher):
        self._content_fetcher = fetcher

    def get_credibility_evaluator(self) -> ICredibilityEvaluator:
        if self._credibility_evaluator is None:
            from veritas.services.credibility_service import RuleBasedCredibilityEvaluator
            self._credibility_evaluator = RuleBasedCredibilityEvaluator()
        return self._credibility_evaluator

    def set_credibility_evaluator(self, evaluator: ICredibilityEvaluator):
        self._credibility_evaluator = evaluator

    def get_image_forensics_service(self) -> IImageForensicsService:
        if self._image_forensics_service is None:
            from veritas.services.image_service import PillowImageForensicsService
            self._image_forensics_service = PillowImageForensicsService()
        return self._image_forensics_service

    def set_image_forensics_service(self, service: IImageForensicsService):
        self._image_forensics_service = service

    def get_reverse_image_provider(self) -> IReverseImageProvider:
        if self._reverse_image_provider is None:
            from veritas.services.image_service import WebReverseImageProvider
            self._reverse_image_provider = WebReverseImageProvider(self.get_search_provider())
        return self._reverse_image_provider

    def set_reverse_image_provider(self, provider: IReverseImageProvider):
        self._reverse_image_provider = provider

    def get_video_forensics_service(self) -> IVideoForensicsService:
        if self._video_forensics_service is None:
            from veritas.services.video_service import OpenCVDeepfakeForensicsService
            self._video_forensics_service = OpenCVDeepfakeForensicsService()
        return self._video_forensics_service

    def set_video_forensics_service(self, service: IVideoForensicsService):
        self._video_forensics_service = service

    def get_claim_dedup_service(self) -> IClaimDedupService:
        if self._claim_dedup_service is None:
            from veritas.services.dedup_service import SemanticClaimDedupService
            self._claim_dedup_service = SemanticClaimDedupService()
        return self._claim_dedup_service

    def set_claim_dedup_service(self, service: IClaimDedupService):
        self._claim_dedup_service = service

    def get_ledger_repository(self) -> ILedgerRepository:
        if self._ledger_repository is None:
            from veritas.services.ledger_service import get_ledger_repository
            self._ledger_repository = get_ledger_repository()
        return self._ledger_repository

    def set_ledger_repository(self, repository: ILedgerRepository):
        self._ledger_repository = repository

    def get_graph_repository(self) -> IGraphRepository:
        if self._graph_repository is None:
            from veritas.services.neo4j_service import get_graph_repository
            self._graph_repository = get_graph_repository()
        return self._graph_repository

    def set_graph_repository(self, repository: IGraphRepository):
        self._graph_repository = repository

# Global default container instance
container = DependencyContainer()
