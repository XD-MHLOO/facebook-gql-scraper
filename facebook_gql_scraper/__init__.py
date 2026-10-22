from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("facebook-gql-scraper")
except PackageNotFoundError:
    __version__ = "unknown"
    
from .exceptions import *

from .structures import (
    Photo as Photo,
    Video as Video,
    GenericMedia as GenericMedia,
    Sticker as Sticker,
    GroupMember as GroupMember,
    Reactor as Reactor,
    FrozenPaginatedIterator as FrozenPaginatedIterator,
    PaginatedIterator as PaginatedIterator,
    FacebookModel as FacebookModel,
    Post as Post,
    Profile as Profile,
    Comment as Comment,
    Group as Group,
    MarketplaceListing as MarketplaceListing,
    SearchEngine as SearchEngine,
)

from .facebookGraphql import (
    FacebookContext as FacebookContext,
)
from .facebookConsolidater import (
    consolidate_jsonl as consolidate_jsonl
)

from .unifiedFacebookParser import (
    parse_facebook_payload as parse_facebook_payload
)

from .facebookNoiseRemoval import (
    remove_raw_facebook_json_noise as remove_raw_facebook_json_noise
)

from .facebookOperationDiscovery import (
    FacebookOperationDiscovery as FacebookOperationDiscovery
)