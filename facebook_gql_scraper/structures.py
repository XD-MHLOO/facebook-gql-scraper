from typing import NamedTuple, Optional, Iterator, TypeVar, Literal, overload
import re
from urllib.parse import urlsplit, urlunsplit


from .facebookGraphql import (
    FacebookContext,
    ProfileCometAboutAppSectionQueryGraphQL,
    ProfileCometHeaderQueryGraphQL,
    ProfileCometAppCollectionListRendererPaginationQueryGraphQL,
    ProfileCometAppCollectionReelsRendererPaginationQueryGraphQL,
    ProfileCometTimelineFeedRefetchQueryGraphQL,
    CometSinglePostDialogContentQueryGraphQL,
    CommentsListComponentsPaginationQueryGraphQL,
    Depth1CommentsListPaginationQueryGraphQL,
    Depth2CommentsListPaginationQueryGraphQL,
    CometUFIReactionsDialogTabContentRefetchQueryGraphQL,
    CometHovercardQueryRendererQueryGraphQL,
    CometGroupAboutRootQueryGraphQL,
    GroupsCometFeedRegularStoriesPaginationQueryGraphQL,
    GroupsCometMembersPageNewMembersSectionRefetchQueryGraphQL,
    SearchCometResultsPaginatedResultsQueryGraphQL,
    CometMarketplaceSearchContentPaginationQueryGraphQL,
    MarketplacePDPContainerQueryGraphQL,
    MarketplacePDPC2CMediaViewerWithImagesQueryGraphQL,
)
from .exceptions import (
    FollowersNotAvailableException,
    FolloweesNotAvailableException,
    FriendFollowersNotAvailableException,
    FriendFolloweesNotAvailableException,
    PhotoNotAvailableException,
    ReelsNotAvailableException,
    MissingParentError,
    ProfileNotFoundError,
    PostNotFoundError,
    GroupNotFoundError,
    MarketplaceListingNotFoundError,
)


class Photo(NamedTuple):
    """
    Facebook photo.

    :ivar id: Unique identifier of the photo.
    :vartype id: str or None
    :ivar image_url: Direct URL of the photo image.
    :vartype image_url: str or None
    :ivar url: Facebook URL of the photo.
    :vartype url: str or None
    """

    id: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


class Video(NamedTuple):
    """
    Facebook video. (Also known as reel)

    :ivar id: Unique identifier of the video.
    :vartype id: str or None
    :ivar length_in_second: Duration of the video in seconds.
    :vartype length_in_second: int or None
    :ivar created_time: Creation timestamp of the video.
    :vartype created_time: int or None
    :ivar thumbnail_image_url: URL of the video's thumbnail image.
    :vartype thumbnail_image_url: str or None
    :ivar video_url: Direct URL of the video.
    :vartype video_url: str or None
    :ivar url: Facebook URL of the video.
    :vartype url: str or None
    :ivar play_count: Number of times the video has been played.
    :vartype play_count: int or None
    :ivar fallback_image_url: Fallback image URL for the video.
    :vartype fallback_image_url: str or None
    """

    id: Optional[str] = None
    length_in_second: Optional[int] = None
    created_time: Optional[int] = None
    thumbnail_image_url: Optional[str] = None
    video_url: Optional[str] = None
    url: Optional[str] = None
    play_count: Optional[int] = None
    fallback_image_url: Optional[str] = None


class GenericMedia(NamedTuple):
    """
    Generic Facebook media attachment.

    :ivar id: Unique identifier of the media object.
    :vartype id: str or None
    :ivar image_url: URL of the media image.
    :vartype image_url: str or None
    :ivar genericMedia_url: URL associated with the generic media.
    :vartype genericMedia_url: str or None
    :ivar animated_image_attribution: Attribution information for animated media.
    :vartype animated_image_attribution: str or None
    """

    id: Optional[str] = None
    image_url: Optional[str] = None
    genericMedia_url: Optional[str] = None
    animated_image_attribution: Optional[str] = None


class Sticker(NamedTuple):
    """
    Facebook sticker attachment.

    :ivar id: Unique identifier of the sticker.
    :vartype id: str or None
    :ivar label: Human-readable sticker label.
    :vartype label: str or None
    :ivar image_url: URL of the sticker image.
    :vartype image_url: str or None
    """

    id: Optional[str] = None
    label: Optional[str] = None
    image_url: Optional[str] = None


class GroupMember(NamedTuple):
    """
    Represents a member of a Facebook group.

    :ivar join_status: Membership or join status of the user.
    :vartype join_status: str or None
    :ivar contribution_score: Contribution score associated with the member.
    :vartype contribution_score: str or None
    :ivar profile: Profile of the group member.
    :vartype profile: Profile or None
    """

    join_status: Optional[str] = None
    contribution_score: Optional[str] = None
    profile: Optional["Profile"] = None


class Reactor(NamedTuple):
    """
    Represents a user who reacted to a Facebook object (either Post or Comment).

    :ivar reaction_type_id: Identifier of the reaction type.
    :vartype reaction_type_id: str or None
    :ivar profile: Profile of the user who reacted.
    :vartype profile: Profile or None
    """

    reaction_type_id: Optional[str] = None
    profile: Optional["Profile"] = None


class Seller(NamedTuple):
    """
    Marketplace seller wrapper.

    A seller is a :class:`Profile` plus Marketplace-specific attributes
    (verified badge, ratings as seller, ratings as seller + buyer).

    :ivar profile: The seller's Facebook profile.
    :vartype profile: Profile or None
    :ivar is_verified: Whether the seller has a verified badge.
    :vartype is_verified: bool or None
    :ivar seller_ratings_average: Average seller-only rating.
    :vartype seller_ratings_average: float or None
    :ivar seller_ratings_count: Total seller-only rating count.
    :vartype seller_ratings_count: int or None
    :ivar seller_ratings_are_private: Whether seller-only ratings are hidden.
    :vartype seller_ratings_are_private: bool or None
    :ivar combined_ratings_average: Average combined rating.
    :vartype combined_ratings_average: float or None
    :ivar combined_ratings_count: Total combined rating count.
    :vartype combined_ratings_count: int or None
    :ivar combined_ratings_are_private: Whether combined ratings are hidden.
    :vartype combined_ratings_are_private: bool or None
    """

    profile: Optional["Profile"] = None
    is_verified: Optional[bool] = None

    seller_ratings_are_private: Optional[bool] = None
    seller_ratings_average: Optional[float] = None
    seller_ratings_count: Optional[int] = None

    combined_ratings_are_private: Optional[bool] = None
    combined_ratings_average: Optional[float] = None
    combined_ratings_count: Optional[int] = None


class PartnerSeller(NamedTuple):
    """
    PartnerSeller marketplace information, e.g. eBay.

    :ivar profile: The partner seller profile.
    :vartype profile: Profile or None
    :ivar partner_brand_name: Partner marketplace brand, e.g. "eBay".
    :vartype partner_brand_name: str or None
    :ivar seller_review_count: Total reviews/feedback for the partner seller.
    :vartype seller_review_count: int or None
    :ivar seller_positive_ratings_pct: Positive rating percentage.
    :vartype seller_positive_ratings_pct: float or None
    :ivar seller_member_since: Partner seller membership timestamp/value.
    :vartype seller_member_since: int or None
    :ivar number_of_sold_listings: Number of sold listings.
    :vartype number_of_sold_listings: int or None
    :ivar average_ship_time: Average shipping time.
    :vartype average_ship_time: str or None
    """

    profile: Optional["Profile"] = None

    partner_brand_name: Optional[str] = None

    seller_review_count: Optional[int] = None
    seller_positive_ratings_pct: Optional[float] = None
    seller_member_since: Optional[int] = None
    number_of_sold_listings: Optional[int] = None
    average_ship_time: Optional[str] = None


def safe_get(data, *keys, default=None):
    """Walk nested dicts/lists. Return default if anything is missing."""
    for key in keys:
        try:
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[key]
            else:
                return default
        except (KeyError, IndexError, TypeError):
            return default
    if data is None:
        return default

    return data


def _attachment_to_dict(attachment: dict) -> Optional[dict]:
    """
    Convert a dict attachment into its normalized dictionary representation based on its type.
    """

    t = attachment.get("type")
    if t == "photo":
        return {
            "type": "photo",
            "id": attachment.get("id"),
            "image_url": attachment.get("image_url"),
            "url": attachment.get("url"),
        }
    elif t == "video":
        return {
            "type": "video",
            "id": attachment.get("id"),
            "length_in_second": attachment.get("length_in_second"),
            "thumbnail_image_url": attachment.get("thumbnail_image_url"),
            "fallback_image_url": attachment.get("fallback_image_url"),
            "video_url": attachment.get("video_url"),
            "url": attachment.get("url"),
        }
    elif t == "genericMedia":
        return {
            "type": "genericMedia",
            "id": attachment.get("id"),
            "image_url": attachment.get("image_url"),
            "genericMedia_url": attachment.get("genericMedia_url"),
            "animated_image_attribution": attachment.get("animated_image_attribution"),
        }
    elif t == "sticker":
        return {
            "type": "sticker",
            "id": attachment.get("id"),
            "label": attachment.get("label"),
            "image_url": attachment.get("image_url"),
        }


def _dict_to_attachment(att: dict) -> Optional[Photo | Video | GenericMedia | Sticker]:
    """Convert a raw attachment dict into a typed NamedTuple, or None for unknown types."""
    t = att.get("type")
    if t == "photo":
        return Photo(
            id=att.get("id"),
            image_url=att.get("image_url"),
            url=att.get("url"),
        )
    elif t == "video":
        return Video(
            id=att.get("id"),
            length_in_second=att.get("length_in_second"),
            created_time=att.get("created_time"),
            thumbnail_image_url=att.get("thumbnail_image_url"),
            video_url=att.get("video_url"),
            url=att.get("url"),
            play_count=att.get("play_count"),
            fallback_image_url=att.get("fallback_image_url"),
        )
    elif t == "genericMedia":
        return GenericMedia(
            id=att.get("id"),
            image_url=att.get("image_url"),
            genericMedia_url=att.get("genericMedia_url"),
            animated_image_attribution=att.get("animated_image_attribution"),
        )
    elif t == "sticker":
        return Sticker(
            id=att.get("id"),
            label=att.get("label"),
            image_url=att.get("image_url"),
        )
    return None


class FrozenPaginatedIterator(NamedTuple):
    """
    Serializable state of a :class:`PaginatedIterator`.

    A frozen iterator contains enough pagination state to resume iteration
    later using :meth:`PaginatedIterator.thaw`.

    :ivar iterator_type: Identifier used to validate iterator resumption.
    :vartype iterator_type: str or None
    :ivar query_variables: Variables identifying the original query.
    :vartype query_variables: dict
    :ivar remaining_raw: Items already fetched but not yet consumed.
    :vartype remaining_raw: list
    :ivar cursor: Cursor used to request the next page.
    :vartype cursor: str or None
    :ivar has_next_page: Whether additional pages are available.
    :vartype has_next_page: bool
    """

    iterator_type: Optional[str]
    query_variables: dict
    remaining_raw: list
    cursor: Optional[str]
    has_next_page: bool


T = TypeVar("T")


class PaginatedIterator(Iterator[T]):
    """
    Lazy iterator for paginated Facebook API responses.

    The iterator requests pages only when the currently buffered items have
    been consumed. Each raw item is converted into the corresponding SDK
    model using ``item_wrapper``.

    :param request_fn: Function receiving the current cursor and returning
        the raw API response.
    :type request_fn: callable
    :param parser: Function that converts the raw API response into parsed data.
    :type parser: callable
    :param page_wrapper: Function converting parsed page data into a tuple
        containing raw items and page information.
    :type page_wrapper: callable
    :param item_wrapper: Function converting a raw item into an SDK object.
    :type item_wrapper: callable
    :param iterator_type: Identifier used to validate iterator resumption.
    :type iterator_type: str or None
    :param query_variables: Variables identifying the pagination query.
    :type query_variables: dict or None
    """

    def __init__(
        self,
        request_fn,
        parser,
        page_wrapper,
        item_wrapper,
        iterator_type=None,
        query_variables=None,
    ):
        self._request_fn = request_fn
        self._parser = parser
        self._page_wrapper = page_wrapper  # convert parsed response into -> (list_of_raw_dicts, page_info)
        self._item_wrapper = item_wrapper  # convert raw_dict -> model
        self._iterator_type = iterator_type
        self._query_variables = query_variables or {}

        self._raw_buffer = []
        self._cursor = None
        self._exhausted = False
        self._page_info = {}

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        """
        Return the next item from the pagination stream.

        A new page is requested automatically when the current page has
        been exhausted.
        """
        while not self._raw_buffer:
            if self._exhausted:
                raise StopIteration
            self._load_next_page()
        raw = self._raw_buffer.pop(0)
        return self._item_wrapper(raw)

    def _load_next_page(self):
        """
        Request and load the next page of results.
        """
        raw = self._request_fn(self._cursor)
        parsed = self._parser(raw)

        if parsed is None:
            self._exhausted = True
            return

        raw_items, page_info = self._page_wrapper(parsed)
        self._raw_buffer = list(raw_items)
        self._page_info = page_info

        if page_info.get("has_next_page") and page_info.get("end_cursor"):
            self._cursor = page_info["end_cursor"]
        else:
            self._exhausted = True

    @classmethod
    def empty(cls, iterator_type=None, query_variables=None):
        """Return an iterator that yields no items."""
        iterator = cls(
            request_fn=None,
            parser=None,
            page_wrapper=None,
            item_wrapper=None,
            iterator_type=iterator_type,
            query_variables=query_variables,
        )
        iterator._exhausted = True
        return iterator

    def freeze(self) -> FrozenPaginatedIterator:
        return FrozenPaginatedIterator(
            iterator_type=self._iterator_type,
            query_variables=self._query_variables,
            remaining_raw=list(self._raw_buffer),
            cursor=self._cursor,
            has_next_page=not self._exhausted,
        )

    def thaw(self, frozen: FrozenPaginatedIterator) -> None:
        if self._raw_buffer or self._cursor is not None:
            raise ValueError("thaw() called on already-used iterator.")
        if (
            self._iterator_type != frozen.iterator_type
            or self._query_variables != frozen.query_variables
        ):
            raise ValueError("Mismatching resume information.")
        self._raw_buffer = list(frozen.remaining_raw or [])
        self._cursor = frozen.cursor
        self._exhausted = not frozen.has_next_page


class FacebookModel:
    """
    Base class for Facebook SDK model objects.

    :param context: Facebook context used for API requests.
    :type context: FacebookContext
    :param data: Initial model data.
    :type data: dict
    """

    def __init__(self, context: FacebookContext, data: dict):
        self._context = context
        self._data = data

    def __eq__(self, o):
        return isinstance(o, type(self)) and self._identity == o._identity

    def __hash__(self):
        return hash(self._identity)

    def _asdict(self):
        return dict(self._data)

    def _obtain_metadata(self):
        """
        Fetch and merge additional metadata into the model.

        Subclasses override this method with their corresponding Facebook
        GraphQL requests.
        """

    def ensure_full_metadata(self):
        """
        Fetch full metadata if not already fetched.
        Metadata is merged into the model's existing internal data.
        """
        self._obtain_metadata()

    @property
    def _identity(self):
        """
        Return the unique identity of the model.
        """
        raise NotImplementedError

    def _field(self, path, default=None):
        """
        Retrieve a field from the model, fetching metadata when necessary.

        :param path: Field name or nested path to retrieve.
        :type path: str or tuple
        :param default: Value returned when the field is unavailable.
        :type default: object
        :return: Value stored at the requested path, or ``default``.
        :rtype: object
        """
        if isinstance(path, str):
            path = (path,)

        def _walk():
            d = self._data
            for k in path:
                d = d[k]
            return d

        try:
            return _walk()
        except (KeyError, TypeError, IndexError):
            self._obtain_metadata()

        try:
            return _walk()
        except (KeyError, TypeError, IndexError):
            return default


class Post(FacebookModel):
    """
    Facebook post.

    A :class:`Post` object is normally created by methods such as
    :meth:`Profile.get_posts` or :meth:`Group.get_posts`.

    Post objects may initially contain only partial information. Additional
    metadata is fetched automatically when a requested field is not available.

    :param context: :class:`FacebookContext` used for additional GraphQL
        requests when more information is required.
    :param data: Dictionary containing the initial post data.
    :param owner: The :class:`Profile` that owns the post, if already known.
    :param group: The :class:`Group` containing the post, if applicable.
    """

    def __init__(
        self,
        context: FacebookContext,
        data: dict,
        owner: "Profile" = None,
        group: "Group" = None,
    ):
        super().__init__(context, data)
        assert "id" in self._data, "Post requires id"
        self._full_fetched = False
        self._owner = owner
        self._group = group

    @property
    def _identity(self) -> str:
        """
        Return the post's unique identifier.

        :return: Facebook post ID.
        :rtype: str
        """
        return self._field("id")

    def _obtain_metadata(self):
        """
        Fetch complete post metadata from Facebook.

        """
        if self._full_fetched:
            return

        post_graphql = CometSinglePostDialogContentQueryGraphQL(self._context)
        response_post_graphql = post_graphql.send(postId=self.id)
        parsed = self._context.parse_graphql_response(response_post_graphql.text)

        if parsed["parsed_data"] is None:
            raise PostNotFoundError(f"Post not found: {self.id}")

        post_data = {
            "id": parsed["parsed_data"]["post"]["id"],
            "creation_time": parsed["parsed_data"]["post"]["creation_time"],
            "url": parsed["parsed_data"]["post"]["url"],
            "author": {
                "id": parsed["parsed_data"]["post"]["author"]["id"],
                "name": parsed["parsed_data"]["post"]["author"]["name"],
                "url": parsed["parsed_data"]["post"]["author"]["url"],
                "profile_picture_url": parsed["parsed_data"]["post"]["author"]["profile_picture_url"],
            },
            "title": parsed["parsed_data"]["post"]["title"],
            "text": parsed["parsed_data"]["post"]["text"],
            "attachments": [
                _attachment_to_dict(a)
                for a in parsed["parsed_data"]["post"]["attachments"]
            ],
            "reactors_visible": parsed["parsed_data"]["post"]["reactors_visible"],
            "reactions": {
                "total": parsed["parsed_data"]["post"]["reactions"]["total"],
                "breakdown": [
                    {
                        "id": entry["id"],
                        "name": entry["name"],
                        "count": entry["count"],
                    }
                    for entry in parsed["parsed_data"]["post"]["reactions"]["breakdown"]
                ],
            },
            "share_count": parsed["parsed_data"]["post"]["share_count"],
            "comments_count": parsed["parsed_data"]["post"]["comments_count"],
        }
        self._data.update(post_data)
        self._full_fetched = True

    @property
    def id(self) -> str:
        """
        Unique identifier of the post.

        :return: The Facebook post ID.
        :rtype: str
        """
        return self._field("id")

    @property
    def creation_time(self) -> Optional[int]:
        """
        Unix timestamp representing when the post was created.

        :return: Post creation timestamp.
        :rtype: int or None
        """
        return self._field("creation_time")

    @property
    def url(self) -> Optional[str]:
        """
        Facebook URL of the post.

        :return: URL of the post.
        :rtype: str or None
        """
        return self._field("url")

    @property
    def title(self) -> Optional[str]:
        """
        Title of the post.

        :return: Post title.
        :rtype: str or None
        """
        return self._field("title")

    @property
    def text(self) -> Optional[str]:
        """
        Text content of the post.

        :return: Post text.
        :rtype: str or None
        """
        return self._field("text")

    # ---------- reactions ----------

    @property
    def reaction_count(self) -> Optional[str]:
        """
        Return the total number of reactions on the post.

        :return: Number of reactions.
        :rtype: str
        """
        return self._field(("reactions", "total"))

    @property
    def reactors_visible(self) -> Optional[bool]:
        """
        Return whether the reactors are visible.

        :return: True if the reactors are visible, otherwise False.
        :rtype: bool
        """
        return self._field(("reactors_visible"))

    @property
    def top_reaction_breakdown(self) -> Optional[list]:
        """
        Return the top reaction count broken down by reaction type.

        :return: List containing reaction type information and counts.
        :rtype: list
        """
        return self._field(("reactions", "breakdown"))

    # ---------- counts ----------

    @property
    def share_count(self) -> Optional[int]:
        """
        Return the number of times the post has been shared.

        :return: Share count.
        :rtype: int
        """
        return self._field("share_count")

    @property
    def comments_count(self) -> Optional[int]:
        """
        Return the number of comments on the post.

        :return: Comment count.
        :rtype: int
        """
        return self._field("comments_count")

    def get_comments(self) -> PaginatedIterator["Comment"]:
        """
        Iterate over all comments of the post.

        Comments are fetched lazily from Facebook using the GraphQL API.

        :return: Iterator yielding :class:`Comment` objects.
        :rtype: PaginatedIterator
        """
        comments_graphql = CommentsListComponentsPaginationQueryGraphQL(self._context)

        def request_fn(cursor):
            return comments_graphql.send(
                postId=self._field("id"),
                commentsAfterCursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "text": item["text"],
                    "attachments": [
                        _attachment_to_dict(att) for att in item["attachments"]
                    ],
                    "created_time": item["created_time"],
                    "reaction_count": item["reaction_count"],
                    "reply_count": item["reply_count"],
                    "reply_expansion_token": item["reply_expansion_token"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "gender": item["author"]["gender"],
                        "url": item["author"]["url"],
                        "profile_picture_url": item["author"]["profile_picture_url"],
                    },
                }
                for item in parsed["parsed_data"]["comments"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Comment(self._context, raw, post=self)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="comments",
            query_variables={"postId": self.id},
        )

    def get_reactors(self) -> PaginatedIterator[Reactor]:
        """
        Iterate over users who reacted to the post.

        :return: Iterator yielding :class:`Reactor` objects.
        :rtype: PaginatedIterator
        """
        reactors_graphql = CometUFIReactionsDialogTabContentRefetchQueryGraphQL(
            self._context
        )

        def request_fn(cursor):
            return reactors_graphql.send(
                postId=self._field("id"),
                reactionID=None,
                itemType="post",
                cursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "reaction_type_id": item["reaction_type_id"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "url": item["author"]["url"],
                        "profile_picture_url": item["author"]["profile_picture_url"],
                    },
                }
                for item in parsed["parsed_data"]["reactors"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Reactor(
                reaction_type_id=raw["reaction_type_id"],
                profile=Profile(self._context, raw["author"]),
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="reactors",
            query_variables={"postId": self.id, "type": "post"},
        )

    @property
    def attachments(self) -> Optional[list[Photo | Video | GenericMedia | Sticker]]:
        """
        Return the post's media attachments as typed objects.

        Unknown attachment types are ignored.

        :return: List of :class:`Photo`, :class:`Video`,
            :class:`GenericMedia`, and :class:`Sticker` objects.
        :rtype: list
        """
        if self._field("attachments") is None:
            return None

        result = []
        for att in self._field("attachments", default=[]):
            converted = _dict_to_attachment(att)
            if converted is not None:
                result.append(converted)
        return result

    @property
    def owner(self) -> Optional["Profile"]:
        """
        Return the profile that owns the post.

        If the owner was not supplied when the post was created, a
        :class:`Profile` object is constructed from the post author data.

        :return: Post owner, or ``None`` when no author information exists.
        :rtype: Profile or None
        """
        if self._owner:
            return self._owner

        if self._field("author", None) is not None:
            data = self._field("author")

            return Profile(
                self._context,
                {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "url": data.get("url"),
                    "profile_picture_url": data.get("profile_picture_url"),
                },
            )

        return None

    @property
    def group(self) -> Optional["Group"]:
        """
        Return the group associated with the post.

        :return: Parent group, or ``None`` when the post is not associated
            with a known group.
        :rtype: Group or None
        """
        return self._group

    @classmethod
    def from_post_id(
        cls,
        context: FacebookContext,
        post_id: str,
    ) -> "Post":
        """
        Create a post from its Facebook ID.
        Automatically Fetch full post metadata

        :param context: Facebook context used to fetch the post.
        :type context: FacebookContext
        :param post_id: Facebook post identifier.
        :type post_id: str
        :return: Post with its metadata fetched.
        :rtype: Post
        """
        post = cls(context, {"id": post_id})
        post._obtain_metadata()
        return post

    @classmethod
    def from_pfbid(
        cls,
        context: FacebookContext,
        pfbid: str,
    ) -> "Post":
        """
        Create a post from its Facebook PFBID.

        Example:
            post = Post.from_pfbid(ctx, "pfbid...")

        :param context: Facebook context used to fetch the post.
        :param pfbid: Facebook PFBID.
        :raises PostNotFoundError: If no matching post is found.
        :return: Post with metadata fetched.
        :rtype: Post
        """

        # Facebook will redirect this URL to the actual post URL.
        url = f"https://web.facebook.com/{pfbid}"
        res = context.get(url)

        final_url = res.url

        # Normalize the final URL.
        p = urlsplit(final_url)
        clean = urlunsplit(
            (
                "https",
                p.netloc,
                p.path.rstrip("/"),
                "",
                "",
            )
        )

        normalized_post_url = re.escape(clean).replace("/", r"\\/")

        pattern = rf'"post_id":"(\d+)"}},\"url\":\"{normalized_post_url}"'
        match = re.search(pattern, res.text)

        post_id = match.group(1) if match else None

        if post_id:
            return cls.from_post_id(context, post_id)

        raise PostNotFoundError(
            f"No post found for PFBID: {pfbid} (final URL: {final_url})"
        )


class Profile(FacebookModel):
    """
    Facebook user profile.

    A profile can initially be created with only its ID. Additional profile
    information is fetched lazily when properties requiring metadata are
    accessed.

    :param context: Facebook context used for GraphQL requests.
    :type context: FacebookContext
    :param data: Initial profile data.
    :type data: dict
    """

    def __init__(self, context, data):
        super().__init__(context, data)
        assert "id" in self._data, "User requires id"
        self._full_fetched = False

    @property
    def _identity(self) -> str:
        """
        Return the profile's unique identifier.
        """
        return self._field("id")

    def _obtain_metadata(self):
        if self._full_fetched:
            return

        user_collection_ids_graphql = ProfileCometHeaderQueryGraphQL(self._context)
        response_user_collection_ids = user_collection_ids_graphql.send(userId=self.id)
        parsed_user_collection_ids = self._context.parse_graphql_response(
            response_user_collection_ids.text
        )

        if parsed_user_collection_ids["parsed_data"] is None:
            raise ProfileNotFoundError(f"Profile not found: {self.id}")

        user_about_collection_graphql = ProfileCometAboutAppSectionQueryGraphQL(
            self._context
        )

        about_section_token = parsed_user_collection_ids["parsed_data"]["tabs"]["About"][
            "id"
        ]

        def _fetch_about(collection_name):
            """Return parsed About payload for a collection, or {} if token is missing."""
            token = safe_get(
                parsed_user_collection_ids,
                "parsed_data",
                "tabs",
                "About",
                "collections",
                collection_name,
            )
            if token is None or about_section_token is None:
                return {}
            response = user_about_collection_graphql.send(
                userId=self.id,
                sectionToken=about_section_token,
                collectionToken=token,
            )
            return self._context.parse_graphql_response(response.text) or {}

        # directory_basic_info
        parsed_directory_basic_info = _fetch_about("directory_basic_info")

        biography = safe_get(
            parsed_directory_basic_info,
            "parsed_data",
            "About",
            "directory_bio",
            "items",
            0,
            "title",
        )

        business_rating = safe_get(
            parsed_directory_basic_info,
            "parsed_data",
            "About",
            "directory_rating_and_reviews",
            "items",
            0,
            "title",
        )
        business_address = safe_get(
            parsed_directory_basic_info,
            "parsed_data",
            "About",
            "directory_business_address",
            "items",
            0,
            "title",
        )
        business_hours = safe_get(
            parsed_directory_basic_info,
            "parsed_data",
            "About",
            "directory_business_hours",
            "items",
            0,
            "title",
        )

        # directory_specialties
        # parsed_directory_specialties = _fetch_about("directory_specialties")

        # directory_intro
        parsed_directory_intro = _fetch_about("directory_intro")
        if biography is None:
            biography = safe_get(
                parsed_directory_intro,
                "parsed_data",
                "About",
                "directory_bio",
                "items",
                0,
                "text",
            )

        # directory_category
        parsed_directory_category = _fetch_about("directory_category")

        category = safe_get(
            parsed_directory_category,
            "parsed_data",
            "About",
            "directory_category",
            "items",
            0,
            "title",
        )

        # directory_personal_details
        parsed_directory_personal_details = _fetch_about("directory_personal_details")

        current_location = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "directory_location",
            "items",
            0,
            "title",
        )
        hometown = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "directory_hometown",
            "items",
            0,
            "title",
        )

        birthday_day = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "directory_birthday",
            "items",
            0,
            "title",
        )
        birthday_year = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "directory_birthday",
            "items",
            1,
            "title",
        )
        birthday = (
            f"{birthday_day} {birthday_year}"
            if (birthday_day or birthday_year)
            else None
        )

        relationship_type = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "relationship",
            "items",
            0,
            "text",
        )
        if relationship_type is None:
            relationship_type = safe_get(
                parsed_directory_personal_details,
                "parsed_data",
                "About",
                "relationship",
                "items",
                0,
                "title",
            )
        relationship = {
            "type": relationship_type,
            "date": safe_get(
                parsed_directory_personal_details,
                "parsed_data",
                "About",
                "relationship",
                "items",
                0,
                "item",
                0,
            ),
            "desc": safe_get(
                parsed_directory_personal_details,
                "parsed_data",
                "About",
                "relationship",
                "items",
                0,
                "item",
                1,
            ),
        }

        family = [
            {
                "name": i.get("title"),
                "type": safe_get(i, "item", 0),
            }
            for i in safe_get(
                parsed_directory_personal_details,
                "parsed_data",
                "About",
                "family",
                "items",
                default=[],
            )
        ]

        language_title = safe_get(
            parsed_directory_personal_details,
            "parsed_data",
            "About",
            "directory_languages",
            "items",
            0,
            "title",
        )
        if language_title:
            language = [
                piece.strip()
                for part in language_title.split(",")
                for piece in part.split(" and ")
                if piece.strip()
            ]
        else:
            language = None

        # directory_links
        parsed_directory_links = _fetch_about("directory_links")

        links = [
            {
                "link": safe_get(i, "item", 0),
                "desc": i.get("title"),
            }
            for i in safe_get(
                parsed_directory_links,
                "parsed_data",
                "About",
                "directory_links",
                "items",
                default=[],
            )
        ]
        # directory_communities
        # parsed_directory_communities = _fetch_about("directory_communities")

        # directory_offers
        # parsed_directory_offers = _fetch_about("directory_offers")

        # directory_work
        parsed_directory_work = _fetch_about("directory_work")

        works = [
            {
                "company": i.get("title"),
                "desc": " | ".join(i.get("item")) if i.get("item") else None,
            }
            for i in safe_get(
                parsed_directory_work,
                "parsed_data",
                "About",
                "directory_work",
                "items",
                default=[],
            )
        ]

        # directory_education
        parsed_directory_education = _fetch_about("directory_education")

        colleges = []
        for i in safe_get(
            parsed_directory_education,
            "parsed_data",
            "About",
            "directory_college",
            "items",
            default=[],
        ):
            if i.get("title") == "University":
                continue
            item_list = i.get("item") or []
            college = {
                "name": i.get("title"),
                "date": safe_get(item_list, 0),
                "subject": None,
                "activities": None,
                "dorm": None,
                "classes": None,
                "desc": None,
            }
            for raw in item_list[1:]:
                text = (raw or "").strip()
                if text.startswith("Subject:"):
                    college["subject"] = text.removeprefix("Subject:").strip()
                elif text.startswith("Activities:"):
                    college["activities"] = text.removeprefix("Activities:").strip()
                elif text.startswith("Dorm:"):
                    college["dorm"] = text.removeprefix("Dorm:").strip()
                elif text.startswith("Classes:"):
                    college["classes"] = text.removeprefix("Classes:").strip()
                elif text.startswith("Description:"):
                    college["desc"] = text.removeprefix("Description:").strip()
            colleges.append(college)

        high_schools = []
        for i in safe_get(
            parsed_directory_education,
            "parsed_data",
            "About",
            "directory_high_school",
            "items",
            default=[],
        ):
            if i.get("title") == "Secondary school":
                continue
            high_schools.append(
                {
                    "name": i.get("title"),
                    "date": safe_get(i, "item", 0),
                }
            )

        # directory_activites
        parsed_directory_activites = _fetch_about("directory_activites")

        hobbies = [
            {
                "name": i.get("title"),
                "desc": safe_get(i, "item", 0),
            }
            for i in safe_get(
                parsed_directory_activites,
                "parsed_data",
                "About",
                "directory_hobbies",
                "items",
                default=[],
            )
        ]

        # directory_interests
        parsed_directory_interests = _fetch_about("directory_interests")

        def _interest_rows(node_key):
            return [
                {
                    "name": i.get("title"),
                    "desc": safe_get(i, "item", 0),
                }
                for i in safe_get(
                    parsed_directory_interests,
                    "parsed_data",
                    "About",
                    node_key,
                    "items",
                    default=[],
                )
            ]

        interests = {
            "musics": _interest_rows("directory_music"),
            "tv_shows": _interest_rows("directory_tv_shows"),
            "movies": _interest_rows("directory_movies"),
            "games": _interest_rows("directory_games"),
            "sports": _interest_rows("directory_sports"),
        }

        # directory_travel
        parsed_directory_travel = _fetch_about("directory_travel")

        travels = []
        for i in safe_get(
            parsed_directory_travel,
            "parsed_data",
            "About",
            "directory_travel",
            "items",
            default=[],
        ):
            raw = safe_get(i, "item", 0)
            if not raw:
                continue
            before, sep, after = raw.rpartition(":")
            travels.append(
                {
                    "name": before.strip() if sep else raw.strip(),
                    "date": after.strip() if sep else None,
                }
            )

        # directory_contact_info
        parsed_directory_contact_info = _fetch_about("directory_contact_info")

        def _contact_rows(node_key):
            return [
                {
                    "type": safe_get(i, "item", 0,
                        default=safe_get(
                            parsed_directory_contact_info,
                            "parsed_data",
                            "About",
                            node_key,
                            "category",
                        ),
                    ),
                    "name": i.get("title"),
                }
                for i in safe_get(
                    parsed_directory_contact_info,
                    "parsed_data",
                    "About",
                    node_key,
                    "items",
                    default=[],
                )
            ]

        contacts = [
            {
                "socials": _contact_rows("directory_socials"),
                "phones": _contact_rows("directory_phone"),
                "emails": _contact_rows("directory_email"),
                "messenger": _contact_rows("directory_messenger"),
                "whatsapp_number": _contact_rows("directory_whatsapp"),
                "media_kit": _contact_rows("directory_media_kit"),
            }
        ]

        # directory_privacy_and_legal_info
        parsed_directory_privacy_and_legal_info = _fetch_about(
            "directory_privacy_and_legal_info"
        )
        description = safe_get(
            parsed_directory_privacy_and_legal_info,
            "parsed_data",
            "About",
            "description",
            "items",
            0,
            "text",
        )

        # directory_names
        parsed_directory_names = _fetch_about("directory_names")

        name_pronunciation = [
            {"name": i.get("text")}
            for i in safe_get(
                parsed_directory_names,
                "parsed_data",
                "About",
                "name_pronunciation",
                "items",
                default=[],
            )
            if i.get("text")
        ]

        nicknames = [
            {
                "type": safe_get(i, "item", 0),
                "name": i.get("title"),
            }
            for i in safe_get(
                parsed_directory_names,
                "parsed_data",
                "About",
                "nicknames",
                "items",
                default=[],
            )
        ]
        user_data = {
            "id": parsed_user_collection_ids["parsed_data"]["author_profile"]["id"],
            "name": parsed_user_collection_ids["parsed_data"]["author_profile"]["name"],
            "alternate_name": parsed_user_collection_ids["parsed_data"]["author_profile"]["alternate_name"],
            "gender": parsed_user_collection_ids["parsed_data"]["author_profile"]["gender"],
            "url": parsed_user_collection_ids["parsed_data"]["author_profile"]["url"],
            "status_text": parsed_user_collection_ids["parsed_data"]["author_profile"]["status_text"],
            "profile_picture_url": parsed_user_collection_ids["parsed_data"]["author_profile"]["profile_picture_url"],
            "is_verified": parsed_user_collection_ids["parsed_data"]["author_profile"]["is_verified"],

            "followers_count": parsed_user_collection_ids["parsed_data"]["author_profile"]["followers_count"],
            "followees_count": parsed_user_collection_ids["parsed_data"]["author_profile"]["followees_count"],
            "friends_count": parsed_user_collection_ids["parsed_data"]["author_profile"]["friends_count"],
            "biography": biography,
            "category": category,
            "current_location": current_location,
            "hometown": hometown,
            "birthday": birthday,
            "relationship": relationship,
            "family": family,
            "language": language,
            "links": links,
            "works": works,
            "colleges": colleges,
            "high_schools": high_schools,
            "hobbies": hobbies,
            "interests": interests,
            "travels": travels,
            "contacts": contacts,
            "description": description,
            "name_pronunciation": name_pronunciation,
            "nicknames": nicknames,
            "business_rating": business_rating,
            "business_address": business_address,
            "business_hours": business_hours,
            "tabs": {
                "About": {
                    "id": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["id"],
                    "collections": {
                        "directory_basic_info": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_basic_info"],
                        "directory_specialties": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_specialties"],
                        "directory_intro": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_intro"],
                        "directory_category": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_category"],
                        "directory_personal_details": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_personal_details"],
                        "directory_links": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_links"],
                        "directory_communities": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_communities"],
                        "directory_offers": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_offers"],
                        "directory_work": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_work"],
                        "directory_education": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_education"],
                        "directory_activites": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_activites"],
                        "directory_interests": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_interests"],
                        "directory_travel": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_travel"],
                        "directory_contact_info": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_contact_info"],
                        "directory_privacy_and_legal_info": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_privacy_and_legal_info"],
                        "directory_names": parsed_user_collection_ids["parsed_data"]["tabs"]["About"]["collections"]["directory_names"],
                    },
                },
                "Followers": {
                    "id": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["id"],
                    "collections": {
                        "followers": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["followers"],
                        "followers_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["followers_mutual"],
                        "following": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["following"],
                        "following_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["following_mutual"],
                        "friends_all": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["friends_all"],
                        "friends_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Followers"]["collections"]["friends_mutual"],
                    },
                },
                "Friends": {
                    "id": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["id"],
                    "collections": {
                        "friends_all": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_all"],
                        "friends_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_mutual"],
                        "friends_recent": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_recent"],
                        "friends_with_upcoming_birthdays": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_with_upcoming_birthdays"],
                        "friends_work": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_work"],
                        "friends_college": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_college"],
                        "friends_high_school": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_high_school"],
                        "friends_current_city": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_current_city"],
                        "friends_hometown": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["friends_hometown"],
                        "followers": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["followers"],
                        "following": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["following"],
                        "followers_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["followers_mutual"],
                        "following_mutual": parsed_user_collection_ids["parsed_data"]["tabs"]["Friends"]["collections"]["following_mutual"],
                    },
                },
                "Photos": {
                    "id": parsed_user_collection_ids["parsed_data"]["tabs"]["Photos"]["id"],
                    "collections": {
                        "photos_by": parsed_user_collection_ids["parsed_data"]["tabs"]["Photos"]["collections"]["photos_by"],
                        "photos_albums": parsed_user_collection_ids["parsed_data"]["tabs"]["Photos"]["collections"]["photos_albums"],
                        "photos_of": parsed_user_collection_ids["parsed_data"]["tabs"]["Photos"]["collections"]["photos_of"],
                    },
                },
                "Reels": {
                    "id": parsed_user_collection_ids["parsed_data"]["tabs"]["Reels"]["id"],
                    "collections": {
                        "owner_reels": parsed_user_collection_ids["parsed_data"]["tabs"]["Reels"]["collections"]["owner_reels"],
                    }
                }
            },
        }

        self._data.update(user_data)
        self._full_fetched = True

    # ---------- identity / profile ----------

    @property
    def id(self) -> str:
        """
        Unique identifier of the Facebook profile.

        :return: Facebook user ID.
        :rtype: str
        """
        return self._field("id")

    @property
    def name(self) -> Optional[str]:
        """
        Display name of the profile.

        :return: Profile name.
        :rtype: str or None
        """
        return self._field("name")

    @property
    def alternate_name(self) -> Optional[str]:
        """
        Alternate name associated with the profile.

        :return: Alternate profile name.
        :rtype: str or None
        """
        return self._field("alternate_name")

    @property
    def gender(self) -> Optional[str]:
        """
        Gender information associated with the profile.

        :return: Gender value.
        :rtype: str or None
        """
        return self._field("gender")

    @property
    def url(self) -> Optional[str]:
        """
        Facebook URL of the profile.

        :return: Profile URL.
        :rtype: str or None
        """
        return self._field("url")

    @property
    def status_text(self) -> Optional[str]:
        """
        Current profile status text.

        :return: Status text.
        :rtype: str or None
        """
        return self._field("status_text")

    @property
    def profile_picture_url(self) -> Optional[str]:
        """
        URL of the profile picture.

        :return: Profile picture URL.
        :rtype: str or None
        """
        return self._field("profile_picture_url")

    @property
    def followers_count(self) -> Optional[str]:
        """
        User's followers count.

        :return: Followers picture URL.
        :rtype: str or None
        """
        return self._field("followers_count")

    @property
    def followees_count(self) -> Optional[str]:
        """
        User's followees count.

        :return: Followees count
        :rtype: str or None
        """
        return self._field("followees_count")

    @property
    def friends_count(self) -> Optional[str]:
        """
        User's friends count.

        :return: Friends count
        :rtype: str or None
        """
        return self._field("friends_count")

    # ---------- about ----------

    @property
    def biography(self) -> Optional[str]:
        """
        Biography of the profile.

        :return: Profile biography.
        :rtype: str or None
        """
        return self._field("biography")

    @property
    def category(self) -> Optional[str]:
        """
        Profile category.

        :return: Category associated with the profile.
        :rtype: str or None
        """
        return self._field("category")

    @property
    def description(self) -> Optional[str]:
        """
        Description associated with the profile.

        :return: Profile description.
        :rtype: str or None
        """
        return self._field("description")

    @property
    def current_location(self) -> Optional[str]:
        """
        Current location set by the profile.

        :return: Current location.
        :rtype: str or None
        """
        return self._field("current_location")

    @property
    def hometown(self) -> Optional[str]:
        """
        Hometown associated with the profile.

        :return: Hometown.
        :rtype: str or None
        """
        return self._field("hometown")

    @property
    def birthday(self) -> Optional[str]:
        """
        Birthday information associated with the profile.

        :return: Birthday representation.
        :rtype: str or None
        """
        return self._field("birthday")

    @property
    def relationship(self) -> Optional[dict]:
        """
        Relationship information associated with the profile.

        :return: Relationship information.
        :rtype: dict or None
        """
        return self._field("relationship")

    @property
    def family(self) -> Optional[list]:
        """
        Family members associated with the profile.

        :return: List of family entries.
        :rtype: list
        """
        return self._field("family")

    @property
    def language(self) -> Optional[list]:
        """
        Languages associated with the profile.

        :return: List of languages, or ``None`` when unavailable.
        :rtype: list or None
        """
        return self._field("language")

    @property
    def links(self) -> Optional[list]:
        """
        External links associated with the profile.

        :return: List of links.
        :rtype: list
        """
        return self._field("links")

    @property
    def works(self) -> Optional[list]:
        """
        Work history associated with the profile.

        :return: List of work entries.
        :rtype: list
        """
        return self._field("works")

    @property
    def colleges(self) -> Optional[list]:
        """
        College or university information associated with the profile.

        :return: List of college entries.
        :rtype: list
        """
        return self._field("colleges")

    @property
    def high_schools(self) -> Optional[list]:
        """
        High school information associated with the profile.

        :return: List of high school entries.
        :rtype: list
        """
        return self._field("high_schools")

    @property
    def hobbies(self) -> Optional[list]:
        """
        Hobbies associated with the profile.

        :return: List of hobbies.
        :rtype: list
        """
        return self._field("hobbies")

    @property
    def interests(self) -> Optional[dict]:
        """
        Interests associated with the profile.

        :return: Dictionary containing categorized interests.
        :rtype: dict
        """
        return self._field("interests")

    @property
    def travels(self) -> Optional[list]:
        """
        Travel information associated with the profile.

        :return: List of travel entries.
        :rtype: list
        """
        return self._field("travels")

    @property
    def contacts(self) -> Optional[list]:
        """
        Contact information associated with the profile.

        :return: List containing categorized contact information.
        :rtype: list
        """
        return self._field("contacts")

    @property
    def name_pronunciation(self) -> Optional[list]:
        """
        Name pronunciation information.

        :return: List of pronunciation entries.
        :rtype: list
        """
        return self._field("name_pronunciation")

    @property
    def nicknames(self) -> Optional[list]:
        """
        Nicknames associated with the profile.

        :return: List of nickname entries.
        :rtype: list
        """

        return self._field("nicknames")

    @property
    def is_verified(self) -> Optional[bool]:
        """
        Whether the profile is verified.

        :return: Verification status.
        :rtype: bool or None
        """

        return self._field("is_verified")

    # ---------- business ----------

    @property
    def business_rating(self) -> Optional[str]:
        """
        Business rating associated with the profile.

        :return: Business rating.
        :rtype: str or None
        """

        return self._field("business_rating")

    @property
    def business_address(self) -> Optional[str]:
        """
        Business address associated with the profile.

        :return: Business address.
        :rtype: str or None
        """

        return self._field("business_address")

    @property
    def business_hours(self) -> Optional[str]:
        """
        Business hours associated with the profile.

        :return: Business hours.
        :rtype: str or None
        """

        return self._field("business_hours")

    @classmethod
    def from_user_id(
        cls,
        context: FacebookContext,
        user_id: str,
    ) -> "Profile":
        """
        Create a profile from its Facebook ID.
        Automatically Fetch full profile metadata

        :param context: Facebook context used to fetch the profile.
        :type context: FacebookContext
        :param user_id: Facebook user ID.
        :type user_id: str
        :return: Profile with metadata fetched.
        :rtype: Profile
        """
        profile = cls(context, {"id": user_id})
        profile._obtain_metadata()
        return profile

    @classmethod
    def from_username(
        cls,
        context: FacebookContext,
        username: str,
    ) -> "Profile":
        """
        Create a profile from its Facebook username.

        Fetches the profile page directly and extracts the user ID from
        the embedded JSON payload.

        :param context: Facebook context used to fetch the profile.
        :type context: FacebookContext
        :param username: Facebook username.
        :type username: str
        :raises ProfileNotFoundError: If no matching profile is found.
        :return: Profile with metadata fetched.
        :rtype: Profile
        """

        res = context.get(f"https://web.facebook.com/{username}")
        match = re.search(r'"userID"\s*:\s*"(\d+)"', res.text)
        user_id = match.group(1) if match else None
        if user_id:
            return cls.from_user_id(context, user_id)

        raise ProfileNotFoundError(f"No profile found for username: {username}")

    def get_followers(self) -> PaginatedIterator["Profile"]:
        """
        Iterate over profiles following this user.

        :return: Iterator yielding :class:`Profile` objects.
        :rtype: PaginatedIterator
        :raises FollowersNotAvailableException: If the follower collection
            is unavailable for this profile.
        """
        user_timeline_app_collection_page_items_graphql = (
            ProfileCometAppCollectionListRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Followers", "collections", "followers"))

        if collection_id is None:
            raise FollowersNotAvailableException(
                f"Follower list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_page_items_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "url": item["url"],
                    "profile_picture_url": item["profile_picture_url"],
                    "is_verified": item["is_verified"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Profile(self._context, raw)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_page_items",
            query_variables={"id": collection_id},
        )

    def get_followees(self) -> PaginatedIterator["Profile"]:
        """
        Iterate over profiles followed by this user.

        :return: Iterator yielding :class:`Profile` objects.
        :rtype: PaginatedIterator
        :raises FolloweesNotAvailableException: If the following collection
            is unavailable for this profile.
        """
        user_timeline_app_collection_page_items_graphql = (
            ProfileCometAppCollectionListRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Followers", "collections", "following"))

        if collection_id is None:
            raise FolloweesNotAvailableException(
                f"Following list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_page_items_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "url": item["url"],
                    "profile_picture_url": item["profile_picture_url"],
                    "is_verified": item["is_verified"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Profile(self._context, raw)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_page_items",
            query_variables={"id": collection_id},
        )

    def get_friends_followers(self) -> PaginatedIterator["Profile"]:
        """
        Iterate over users who have a follower relationship with this user.

        :return: Iterator yielding :class:`Profile` objects.
        :rtype: PaginatedIterator
        :raises FriendFollowersNotAvailableException: If the corresponding
            collection is unavailable.
        """
        user_timeline_app_collection_page_items_graphql = (
            ProfileCometAppCollectionListRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Friends", "collections", "followers"))

        if collection_id is None:
            raise FriendFollowersNotAvailableException(
                f"Friend with follower relationship list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_page_items_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "url": item["url"],
                    "profile_picture_url": item["profile_picture_url"],
                    "is_verified": item["is_verified"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Profile(self._context, raw)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_page_items",
            query_variables={"id": collection_id},
        )

    def get_friends_followees(self) -> PaginatedIterator["Profile"]:
        """
        Iterate over users who this user follows through the friends
        relationship collection.

        :return: Iterator yielding :class:`Profile` objects.
        :rtype: PaginatedIterator
        :raises FriendFolloweesNotAvailableException: If the corresponding
            collection is unavailable.
        """
        user_timeline_app_collection_page_items_graphql = (
            ProfileCometAppCollectionListRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Friends", "collections", "following"))

        if collection_id is None:
            raise FriendFolloweesNotAvailableException(
                f"Friend with following relationship list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_page_items_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "url": item["url"],
                    "profile_picture_url": item["profile_picture_url"],
                    "is_verified": item["is_verified"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Profile(self._context, raw)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_page_items",
            query_variables={"id": collection_id},
        )

    def get_posts(self) -> PaginatedIterator[Post]:
        """
        Iterate over posts published by this profile.

        :return: Iterator yielding :class:`Post` objects.
        :rtype: PaginatedIterator
        """
        timeline_graphql = ProfileCometTimelineFeedRefetchQueryGraphQL(self._context)

        def request_fn(cursor):
            return timeline_graphql.send(userId=self._field("id"), cursor=cursor).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "creation_time": item["creation_time"],
                    "url": item["url"],
                    "title": item["title"],
                    "text": item["text"],
                    "attachments": [
                        _attachment_to_dict(a) for a in item["attachments"]
                    ],
                    "share_count": item["share_count"],
                    "comments_count": item["comments_count"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "url": item["author"]["url"],
                    },
                    "reactors_visible": item["reactors_visible"],
                    "reactions": {
                        "total": item["reactions"]["total"],
                        "breakdown": [
                            {
                                "id": entry["id"],
                                "name": entry["name"],
                                "count": entry["count"],
                            }
                            for entry in item["reactions"]["breakdown"]
                        ],
                    },
                }
                for item in parsed["parsed_data"]["posts"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Post(self._context, raw, owner=self)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timeline",
            query_variables={"userId": self.id},
        )

    def get_photos(self) -> PaginatedIterator[Photo]:
        """
        Iterate over photos associated with this profile.

        :return: Iterator yielding :class:`Photo` objects.
        :rtype: PaginatedIterator
        :raises PhotoNotAvailableException: If the photo collection is
            unavailable for this profile.
        """
        user_timeline_app_collection_page_items_graphql = (
            ProfileCometAppCollectionListRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Photos", "collections", "photos_by"))

        if collection_id is None:
            raise PhotoNotAvailableException(
                f"Photo list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_page_items_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "image_url": item["image_url"],
                    "url": item["url"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Photo(
                id=raw["id"],
                image_url=raw["image_url"],
                url=raw["url"],
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_page_items",
            query_variables={"id": collection_id},
        )

    def get_videos(self) -> PaginatedIterator[Video]:
        """
        Iterate over reels or short-form videos associated with this profile.

        :return: Iterator yielding :class:`Video` objects.
        :rtype: PaginatedIterator
        :raises ReelsNotAvailableException: If the reels collection is
            unavailable for this profile.
        """
        user_timeline_app_collection_aggregated_fb_shorts_graphql = (
            ProfileCometAppCollectionReelsRendererPaginationQueryGraphQL(self._context)
        )
        collection_id = self._field(("tabs", "Reels", "collections", "owner_reels"))

        if collection_id is None:
            raise ReelsNotAvailableException(
                f"Reel list is not available for user {self.id}."
            )

        def request_fn(cursor):
            return user_timeline_app_collection_aggregated_fb_shorts_graphql.send(
                collectionId=collection_id, cursor=cursor
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "length_in_second": item["length_in_second"],
                    "created_time": item["created_time"],
                    "thumbnail_image_url": item["thumbnail_image_url"],
                    "video_url": item["video_url"],
                    "url": item["url"],
                    "play_count": item["play_count"],
                }
                for item in parsed["parsed_data"]["items"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Video(
                id=raw["id"],
                length_in_second=raw["length_in_second"],
                created_time=raw["created_time"],
                thumbnail_image_url=raw["thumbnail_image_url"],
                video_url=raw["video_url"],
                url=raw["url"],
                play_count=raw["play_count"],
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="timelineapp_collection_aggregated_fb_shorts",
            query_variables={"id": collection_id},
        )


class Comment(FacebookModel):
    """
    Facebook comment.

    A comment may belong directly to a :class:`Post` or may itself be a
    reply to another :class:`Comment`.

    :param context: Facebook context used for GraphQL requests.
    :type context: FacebookContext
    :param data: Initial comment data.
    :type data: dict
    :param owner: Profile that authored the comment, if already known.
    :type owner: Profile or None
    :param post: Parent post of the comment.
    :type post: Post or None
    :param comment: Parent comment when this object represents a reply.
    :type comment: Comment or None
    """

    def __init__(
        self,
        context: FacebookContext,
        data: dict,
        owner: Profile = None,
        post: Post = None,
        comment: "Comment" = None,
    ):
        super().__init__(context, data)
        assert "id" in self._data, "Comment requires id"
        self._owner = owner
        self._post = post
        self._comment = comment  # Parent Comment | None

    @property
    def _identity(self):
        return self._field("id")

    @property
    def id(self) -> str:
        """
        Unique identifier of the comment.

        :return: Facebook comment ID.
        :rtype: str
        """
        return self._field("id")

    @property
    def text(self) -> Optional[str]:
        """
        Text content of the comment.

        :return: Comment text.
        :rtype: str or None
        """
        return self._field("text")

    @property
    def created_time(self) -> Optional[int]:
        """
        Creation timestamp of the comment.

        :return: Comment creation timestamp.
        :rtype: int or None
        """
        return self._field("created_time")

    @property
    def reaction_count(self) -> Optional[str]:
        """
        Number of reactions on the comment.

        :return: Reaction count.
        :rtype: str
        """
        return self._field("reaction_count")

    @property
    def reply_count(self) -> int:
        """
        Number of replies to the comment.

        :return: Reply count.
        :rtype: int
        """
        return self._field("reply_count")

    @property
    def _reply_expansion_token(self) -> Optional[str]:
        """
        Token used to retrieve replies to the comment.

        :return: Reply expansion token.
        :rtype: str or None
        """
        return self._field("reply_expansion_token")

    def get_replies(self) -> PaginatedIterator["Comment"]:
        """
        Iterate over replies to this comment.

        Replies are fetched lazily using the parent post ID, comment ID,
        and reply expansion token.

        :return: Iterator yielding reply :class:`Comment` objects.
        :rtype: PaginatedIterator
        :raises MissingParentError: If the comment has no parent post.
        """
        comment_replies_graphql = Depth1CommentsListPaginationQueryGraphQL(self._context)

        if self.post is None:
            raise MissingParentError(
                "Comment has no parent Post. Replies require the parent Post's ID to be fetched."
            )

        if self.reply_count == 0:
            return PaginatedIterator.empty(
                iterator_type="comment_replies",
                query_variables={
                    "postId": self.post.id,
                    "commentId": self.id,
                    "expansionToken": self._reply_expansion_token,
                },
            )

        def request_fn(cursor):
            return comment_replies_graphql.send(
                postId=self.post.id,
                commentId=self.id,
                expansionToken=self._reply_expansion_token,
                repliesAfterCursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "text": item["text"],
                    "attachments": [
                        _attachment_to_dict(att) for att in item["attachments"]
                    ],
                    "created_time": item["created_time"],
                    "reaction_count": item["reaction_count"],
                    "reply_count": item["reply_count"],
                    "reply_expansion_token": item["reply_expansion_token"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "gender": item["author"]["gender"],
                        "url": item["author"]["url"],
                        "profile_picture_url": item["author"]["profile_picture_url"],
                    },
                }
                for item in parsed["parsed_data"]["replies"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Comment(
                self._context,
                raw,
                post=self._post,
                comment=self,
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="comment_replies",
            query_variables={
                "postId": self.post.id,
                "commentId": self.id,
                "expansionToken": self._reply_expansion_token,
            },
        )

    def get_reactors(self) -> PaginatedIterator[Reactor]:
        """
        Iterate over users who reacted to the comment.

        :return: Iterator yielding :class:`Reactor` objects.
        :rtype: PaginatedIterator
        :raises MissingParentError: If the comment has no parent post.
        """
        reactors_graphql = CometUFIReactionsDialogTabContentRefetchQueryGraphQL(
            self._context
        )

        if self.post is None:
            raise MissingParentError(
                "Comment has no parent Post. Accessing reactors require the parent Post's ID to be fetched."
            )

        def request_fn(cursor):
            return reactors_graphql.send(
                postId=self.post.id,
                reactionID=None,
                commentId=self.id,
                itemType="comment",
                cursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "reaction_type_id": item["reaction_type_id"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "url": item["author"]["url"],
                        "profile_picture_url": item["author"]["profile_picture_url"],
                    },
                }
                for item in parsed["parsed_data"]["reactors"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Reactor(
                reaction_type_id=raw["reaction_type_id"],
                profile=Profile(self._context, raw["author"]),
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="reactors",
            query_variables={
                "postId": self.post.id,
                "commentId": self.id,
                "type": "comment",
            },
        )

    @property
    def owner(self) -> Optional["Profile"]:
        """
        Return the profile that authored the comment.

        :return: Comment author, or ``None`` when author information is
            unavailable.
        :rtype: Profile or None
        """
        if self._owner:
            return self._owner

        if self._field("author", None) is not None:
            data = self._field("author")

            return Profile(
                self._context,
                {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "gender": data.get("gender"),
                    "url": data.get("url"),
                    "profile_picture_url": data.get("profile_picture_url"),
                },
            )

        return None

    @property
    def post(self) -> Optional[Post]:
        """
        Return the parent post of the comment.

        :return: Parent post, or ``None`` if no parent post is known.
        :rtype: Post or None
        """
        return self._post

    @property
    def attachments(self) -> Optional[list[Photo | Video | GenericMedia | Sticker]]:
        """
        Return the comment's media attachments as typed objects.

        :return: List of typed attachment objects.
        :rtype: list
        """

        if self._field("attachments") is None:
            return None

        result = []
        for att in self._field("attachments", default=[]):
            converted = _dict_to_attachment(att)
            if converted is not None:
                result.append(converted)
        return result


class Group(FacebookModel):
    """
    Facebook group.

    Group objects may initially contain only a group ID. Additional group
    metadata is fetched lazily when required.

    :param context: Facebook context used for GraphQL requests.
    :type context: FacebookContext
    :param data: Initial group data.
    :type data: dict
    """

    def __init__(self, context: FacebookContext, data: dict):
        super().__init__(context, data)
        assert "id" in self._data, "Group requires id"
        self._full_fetched = False

    @property
    def _identity(self):
        return self._field("id")

    def _obtain_metadata(self):
        """
        Fetch and merge complete group metadata.

        """
        if self._full_fetched:
            return

        group_partial_graphql = CometHovercardQueryRendererQueryGraphQL(self._context)
        response_group_partial_graphql = group_partial_graphql.send(groupId=self.id)
        parsed_group_partial_graphql = self._context.parse_graphql_response(response_group_partial_graphql.text)

        if parsed_group_partial_graphql["parsed_data"] is None:
            raise GroupNotFoundError(
                f"Group not found: {self.id}"
            )

        group_about_info_graphql = CometGroupAboutRootQueryGraphQL(self._context)
        response_group_about_info_graphql = group_about_info_graphql.send(groupId=self.id)
        parsed_group_about_info_graphql = self._context.parse_graphql_response(response_group_about_info_graphql.text)

        group_profile = {
            "id": parsed_group_partial_graphql["parsed_data"]["id"],
            "name": parsed_group_partial_graphql["parsed_data"]["name"],
            "url": parsed_group_partial_graphql["parsed_data"]["url"],
            "privacy": parsed_group_partial_graphql["parsed_data"]["privacy"],
            "member_count": parsed_group_partial_graphql["parsed_data"]["member_count"],
            "profile_picture_url": parsed_group_partial_graphql["parsed_data"]["profile_picture_url"],
            "created_time": parsed_group_about_info_graphql["parsed_data"]["created_time"],
            "description": parsed_group_about_info_graphql["parsed_data"]["description"],
            "privacy_info": parsed_group_about_info_graphql["parsed_data"]["privacy_info"],
            "discoverability_info": parsed_group_about_info_graphql["parsed_data"]["discoverability_info"],
        }

        self._data.update(group_profile)
        self._full_fetched = True

    # ---------- identity ----------

    @property
    def id(self) -> str:
        """
        Unique identifier of the Facebook group.

        :return: Facebook group ID.
        :rtype: str
        """
        return self._field("id")

    @property
    def name(self) -> Optional[str]:
        """
        Name of the Facebook group.

        :return: Group name.
        :rtype: str or None
        """
        return self._field("name")

    @property
    def url(self) -> Optional[str]:
        """
        Facebook URL of the group.

        :return: Group URL.
        :rtype: str or None
        """
        return self._field("url")

    # ---------- metadata ----------

    @property
    def privacy(self) -> Optional[str]:
        """
        Privacy setting of the group.

        :return: Group privacy information.
        :rtype: str or None
        """
        return self._field("privacy")

    @property
    def member_count(self) -> Optional[int]:
        """
        Number of members in the group.

        :return: Group member count.
        :rtype: int or None
        """
        return self._field("member_count")

    @property
    def profile_picture_url(self) -> Optional[str]:
        """
        URL of the group's profile picture.

        :return: Group profile picture URL.
        :rtype: str or None
        """
        return self._field("profile_picture_url")

    @property
    def created_time(self) -> Optional[int]:
        """
        Creation timestamp of the group.

        :return: Group creation timestamp.
        :rtype: int or None
        """
        return self._field("created_time")

    @property
    def description(self) -> Optional[str]:
        """
        Description of the group.

        :return: Group description.
        :rtype: str or None
        """
        return self._field("description")

    @property
    def privacy_info(self) -> Optional[str]:
        """
        Additional privacy information for the group.

        :return: Privacy information.
        :rtype: str or None
        """
        return self._field("privacy_info")

    @property
    def discoverability_info(self) -> Optional[str]:
        """
        Information describing how the group can be discovered.

        :return: Discoverability information.
        :rtype: str or None
        """
        return self._field("discoverability_info")

    def get_posts(self) -> PaginatedIterator[Post]:
        """
        Iterate over posts published in the group.

        :return: Iterator yielding :class:`Post` objects.
        :rtype: PaginatedIterator
        """
        group_timeline_graphql = GroupsCometFeedRegularStoriesPaginationQueryGraphQL(self._context)

        def request_fn(cursor):
            return group_timeline_graphql.send(groupId=self._field("id"), cursor=cursor).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "id": item["id"],
                    "creation_time": item["creation_time"],
                    "url": item["url"],
                    "title": item["title"],
                    "text": item["text"],
                    "attachments": [
                        _attachment_to_dict(a) for a in item["attachments"]
                    ],
                    "share_count": item["share_count"],
                    "comments_count": item["comments_count"],
                    "author": {
                        "id": item["author"]["id"],
                        "name": item["author"]["name"],
                        "url": item["author"]["url"],
                    },
                    "reactors_visible": item["reactors_visible"],
                    "reactions": {
                        "total": item["reactions"]["total"],
                        "breakdown": [
                            {
                                "id": entry["id"],
                                "name": entry["name"],
                                "count": entry["count"],
                            }
                            for entry in item["reactions"]["breakdown"]
                        ],
                    },
                }
                for item in parsed["parsed_data"]["posts"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return Post(self._context, raw, group=self)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="group_timeline",
            query_variables={"groupId": self.id},
        )

    def get_members(self) -> PaginatedIterator[GroupMember]:
        """
        Iterate over members of the group.

        :return: Iterator yielding :class:`GroupMember` objects.
        :rtype: PaginatedIterator
        """
        group_member_graphql = GroupsCometMembersPageNewMembersSectionRefetchQueryGraphQL(self._context)

        def request_fn(cursor):
            return group_member_graphql.send(
                groupId=self.id,
                cursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw_items = [
                {
                    "join_status": item["join_status"],
                    "contribution_score": item["contribution_score"],
                    "account": {
                        "id": item["account"]["id"],
                        "name": item["account"]["name"],
                        "url": item["account"]["url"],
                        "profile_picture_url": item["account"]["profile_picture_url"],
                    },
                }
                for item in parsed["parsed_data"]["members"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return GroupMember(
                join_status=raw["join_status"],
                contribution_score=raw["contribution_score"],
                profile=Profile(self._context, raw["account"]),
            )

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="group_members",
            query_variables={"groupId": self.id},
        )

    # ---------- factory ----------

    @classmethod
    def from_group_id(
        cls,
        context: FacebookContext,
        group_id: str,
    ) -> "Group":
        """
        Create a group from its Facebook ID.
        Automatically Fetch full group metadata

        :param context: Facebook context used to fetch the group.
        :type context: FacebookContext
        :param group_id: Facebook group ID.
        :type group_id: str
        :return: Group with metadata fetched.
        :rtype: Group
        """
        group_profile = cls(context, {"id": group_id})
        group_profile._obtain_metadata()
        return group_profile

    @classmethod
    def from_groupname(
        cls,
        context: FacebookContext,
        groupname: str,
    ) -> "Profile":
        """
        Create a group from its Facebook groupname.

        Fetches the group page directly and extracts the group ID from
        the embedded JSON payload.

        :param context: Facebook context used to fetch the group.
        :type context: FacebookContext
        :param groupname: Facebook groupname.
        :type groupname: str
        :raises GroupNotFoundError: If no matching profile is found.
        :return: Group with metadata fetched.
        :rtype: Group
        """

        res = context.get(f"https://web.facebook.com/groups/{groupname}")
        match = re.search(r'"groupID"\s*:\s*"(\d+)"', res.text)
        group_id = match.group(1) if match else None
        if group_id:
            return cls.from_group_id(context, group_id)

        raise GroupNotFoundError(f"No group found for groupname: {groupname}")


class MarketplaceListing(FacebookModel):
    """
    Facebook Marketplace listing.

    A listing may initially be created with only partial data (from a
    feed or search result). Additional metadata (description, attributes,
    photos, seller ratings, etc.) is fetched lazily when a property
    requiring PDP-level data is accessed.

    :param context: Facebook context used for GraphQL requests.
    :type context: FacebookContext
    :param data: Initial listing data.
    :type data: dict
    :param seller: The :class:`Profile` that owns the listing, if known.
    :type seller: Profile or None
    """

    def __init__(self, context: FacebookContext, data: dict):
        super().__init__(context, data)
        assert "id" in self._data, "MarketplaceListing requires id"
        self._full_fetched = False

    @property
    def _identity(self):
        return self._field("id")

    def _obtain_metadata(self):
        """
        Fetch and merge complete listing metadata.

        :return: ``None``.
        :rty
        """
        if self._full_fetched:
            return

        marketplace_pdp_graphql = MarketplacePDPContainerQueryGraphQL(self._context)
        response_marketplace_pdp_graphql = marketplace_pdp_graphql.send(marketListingId=self.id)
        parsed_marketplace_pdp_graphql = self._context.parse_graphql_response(response_marketplace_pdp_graphql.text)

        if parsed_marketplace_pdp_graphql["parsed_data"] is None:
            raise MarketplaceListingNotFoundError(
                f"Marketplace listing not found: {self.id}"
            )

        # Fetch media separately (Meta splits PDP into two responses)

        marketplace_pdp_media_graphql = MarketplacePDPC2CMediaViewerWithImagesQueryGraphQL(self._context)
        response_marketplace_pdp_media_graphql = marketplace_pdp_media_graphql.send(marketListingId=self.id)
        parsed_marketplace_pdp_media_graphql = self._context.parse_graphql_response(response_marketplace_pdp_media_graphql.text)


        listing = parsed_marketplace_pdp_graphql["parsed_data"]["listing"]
        seller = listing["seller"]
        seller_profile = seller["profile"]
        partner = listing["partner"]
        partner_profile = partner["profile"]
        seller_stats = seller["seller_stats"]
        combined_stats = seller["seller_buyer_combined"]

        market_listing_data = {
            "id": listing["id"],
            "category_id": listing["category_id"],
            "url": listing["url"],
            "post_id": listing["post_id"],
            "creation_time": listing["creation_time"],
            "currency": listing["currency"],
            "price": listing["price"],
            "strikethrough_price": listing["strikethrough_price"],
            "location_text": listing["location_text"],
            "latitude": listing["latitude"],
            "longitude": listing["longitude"],
            "title": listing["title"],
            "description": listing["description"],
            "discounts_text": listing["discounts_text"],
            "is_live": listing["is_live"],
            "is_pending": listing["is_pending"],
            "is_sold": listing["is_sold"],
            "is_hidden": listing["is_hidden"],
            "is_on_marketplace": listing["is_on_marketplace"],
            "seller": {
                "profile": {
                    "id": seller_profile["id"],
                    "name": seller_profile["name"],
                    "profile_picture_url": seller_profile["profile_picture_url"],
                    "joined_time": seller_profile["joined_time"],
                },
                "verified_badge": seller["verified_badge"],
                "seller_ratings_are_private": seller["seller_ratings_are_private"],
                "seller_stats": {
                    "five_star_ratings_average":            seller_stats["five_star_ratings_average"],
                    "five_star_total_rating_count_by_role": seller_stats["five_star_total_rating_count_by_role"],
                },
                "seller_buyer_combined_ratings_are_private": seller["seller_buyer_combined_ratings_are_private"],
                "seller_buyer_combined": {
                    "five_star_ratings_average":            combined_stats["five_star_ratings_average"],
                    "five_star_total_rating_count_by_role": combined_stats["five_star_total_rating_count_by_role"],
                },
            },
            "partner": {
                "profile": {
                    "id": partner_profile["id"],
                    "name": partner_profile["name"],
                    "profile_picture_url": partner_profile["profile_picture_url"],
                },
                "partner_brand_name": partner["partner_brand_name"],
                "seller_review_count": partner["seller_review_count"],
                "seller_positive_ratings_pct": partner["seller_positive_ratings_pct"],
                "seller_member_since": partner["seller_member_since"],
                "number_of_sold_listings": partner["number_of_sold_listings"],
                "average_ship_time": partner["average_ship_time"],
            },
            "shipping_cost_text": listing["shipping_cost_text"],
            "has_shipping_cost": listing["has_shipping_cost"],
            "delivery_window_text": listing["delivery_window_text"],
            "product_details_page_uri": listing["product_details_page_uri"],
            "attributes": [
                {
                    "name": a["name"],
                    "value": a["value"],
                }
                for a in listing["attributes"]
            ],
            "delivery_types": listing["delivery_types"],
            "is_shipping_offered": listing["is_shipping_offered"],
            "is_buy_now_enabled": listing["is_buy_now_enabled"],
            "is_checkout_enabled": listing["is_checkout_enabled"],
            "is_cart_enabled": listing["is_cart_enabled"],
            "is_purchase_protected": listing["is_purchase_protected"],
            "inventory_count": listing["inventory_count"],
            "messaging_enabled": listing["messaging_enabled"],
            "created_with_seller_app": listing["created_with_seller_app"],
            "product_details_type": listing["product_details_type"],
            "photos": [
                {
                    "id": p["id"],
                    "image_url": p["image_url"],
                }
                for p in parsed_marketplace_pdp_media_graphql["parsed_data"]["media"]["photos"]
            ],
            "videos": [
                {
                    "id": v["id"],
                    "thumbnail_image_url": v["thumbnail_image_url"],
                    "video_url": v["playable_url_hd"] if v["playable_url_hd"] is not None else v["playable_url"]
                }
                for v in parsed_marketplace_pdp_media_graphql["parsed_data"]["media"]["videos"]
            ],
        }

        self._data.update(market_listing_data)
        self._full_fetched = True

    # ---------- identity ----------

    @property
    def id(self) -> str:
        """
        Unique identifier of the listing.

        :return: Facebook listing ID.
        :rtype: str
        """
        return self._field("id")

    @property
    def title(self) -> Optional[str]:
        """
        Title of the listing.

        :return: Listing title.
        :rtype: str or None
        """
        return self._field("title")

    @property
    def description(self) -> Optional[str]:
        """
        Full description of the listing.

        :return: Listing description.
        :rtype: str or None
        """
        return self._field("description")

    @property
    def url(self) -> Optional[str]:
        """
        Facebook URL of the listing.

        :return: Listing URL.
        :rtype: str or None
        """
        return self._field("url")

    @property
    def post_id(self) -> Optional[str]:
        """
        Underlying post ID of the listing.

        :return: Post ID.
        :rtype: str or None
        """
        return self._field("post_id")

    @property
    def creation_time(self) -> Optional[int]:
        """
        Unix timestamp when the listing was created.

        :return: Creation timestamp.
        :rtype: int or None
        """
        return self._field("creation_time")

    # ---------- pricing ----------

    @property
    def currency(self) -> Optional[str]:
        """
        ISO 4217 currency code (e.g. ``"USD"``, ``"MYR"``).

        :return: Currency code.
        :rtype: str or None
        """
        return self._field("currency")

    @property
    def price(self) -> Optional[float]:
        """
        Listing price as a decimal value.

        :return: Price amount.
        :rtype: float or None
        """
        return self._field("price")

    @property
    def strikethrough_price(self) -> Optional[float]:
        """
        Original price before discount, if any.

        :return: Strikethrough price.
        :rtype: float or None
        """
        return self._field("strikethrough_price")

    # ---------- location ----------

    @property
    def location_text(self) -> Optional[str]:
        """
        Human-readable location string (e.g. ``"Uxbridge, MA"``).

        :return: Location text.
        :rtype: str or None
        """
        return self._field("location_text")

    @property
    def latitude(self) -> Optional[float]:
        """
        Latitude of the listing.

        :return: Latitude.
        :rtype: float or None
        """
        return self._field("latitude")

    @property
    def longitude(self) -> Optional[float]:
        """
        Longitude of the listing.

        :return: Longitude.
        :rtype: float or None
        """
        return self._field("longitude")

    # ---------- status ----------

    @property
    def is_live(self) -> Optional[bool]:
        """
        Whether the listing is published and active.

        :return: Live status.
        :rtype: bool or None
        """
        return self._field("is_live")

    @property
    def is_pending(self) -> Optional[bool]:
        """
        Whether the listing is pending review or in-progress.

        :return: Pending status.
        :rtype: bool or None
        """
        return self._field("is_pending")

    @property
    def is_sold(self) -> Optional[bool]:
        """
        Whether the listing has been sold.

        :return: Sold status.
        :rtype: bool or None
        """
        return self._field("is_sold")

    @property
    def is_hidden(self) -> Optional[bool]:
        """
        Whether the listing is hidden from public view.

        :return: Hidden status.
        :rtype: bool or None
        """
        return self._field("is_hidden")

    # ---------- category / attributes ----------

    @property
    def category_id(self) -> Optional[str]:
        """
        Marketplace category ID.

        :return: Category ID.
        :rtype: str or None
        """
        return self._field("category_id")

    @property
    def attributes(self) -> Optional[list]:
        """
        Listing attributes (e.g. condition, brand).

        :return: List of attribute entries.
        :rtype: list
        """
        return self._field("attributes")

    # ---------- commerce ----------

    @property
    def delivery_types(self) -> Optional[list]:
        """
        Available delivery methods (e.g. ``["IN_PERSON"]``).

        :return: List of delivery type strings.
        :rtype: list
        """
        return self._field("delivery_types")

    @property
    def is_shipping_offered(self) -> Optional[bool]:
        """
        Whether shipping is offered for this listing.

        :return: Shipping offered flag.
        :rtype: bool or None
        """
        return self._field("is_shipping_offered")

    @property
    def is_purchase_protected(self) -> Optional[bool]:
        """
        Whether the listing is covered by purchase protection.

        :return: Purchase protection flag.
        :rtype: bool or None
        """
        return self._field("is_purchase_protected")

    @property
    def inventory_count(self) -> Optional[int]:
        """
        Available stock count.

        :return: Inventory count.
        :rtype: int or None
        """
        return self._field("inventory_count")

    @property
    def messaging_enabled(self) -> Optional[bool]:
        """
        Whether messaging the seller is enabled.

        :return: Messaging flag.
        :rtype: bool or None
        """
        return self._field("messaging_enabled")

    @property
    def product_details_type(self) -> Optional[str]:
        """
        Marketplace PDP type.

        One of ``"FOR_SALE_ITEM"`` or ``"PARTNER_LISTING"``.

        :return: Product details type, or ``None`` if unavailable.
        :rtype: str or None
        """
        return self._field("product_details_type")

    @property
    def shipping_cost_text(self) -> Optional[str]:
        """
        Return the shipping cost text for the listing.

        For partner listings, this may contain text such as
        ``"Ships for $12"``. Returns ``None`` when shipping cost
        information is unavailable.

        :return: Shipping cost text, or ``None``.
        :rtype: str or None
        """
        return self._field("shipping_cost_text")

    @property
    def has_shipping_cost(self) -> Optional[bool]:
        """
        Return whether the listing has a shipping cost.

        :return: ``True`` when a shipping cost is present, ``False`` when
            shipping is offered without a cost, or ``None`` when the
            information is unavailable.
        :rtype: bool or None
        """
        return self._field("has_shipping_cost")

    @property
    def delivery_window_text(self) -> Optional[str]:
        """
        Return the estimated delivery window for the listing.

        For partner listings, this may contain text such as
        ``"Delivery estimated between Sat, Oct 10 and Sat, Oct 17"``.
        Returns ``None`` when delivery window information is unavailable.

        :return: Delivery window text, or ``None``.
        :rtype: str or None
        """
        return self._field("delivery_window_text")

    @property
    def product_details_page_uri(self) -> Optional[str]:
        """
        Return the external product details page URI.

        For partner listings, this points to the partner's product page,
        such as the corresponding eBay listing. Returns ``None`` when no
        external product page URI is available.

        :return: Product details page URI, or ``None``.
        :rtype: str or None
        """
        return self._field("product_details_page_uri")

    # ---------- media ----------

    @property
    def listing_photos(self) -> Optional[list[Photo]]:
        """
        All photos of the listing.

        Fetched from the PDP media payload on first access.

        :return: List of :class:`Photo` objects.
        :rtype: list
        """

        if self._field("photos") is None:
            return None

        photos = self._field("photos", default=[])
        return [
            Photo(
                id=p.get("id"),
                image_url=p.get("image_url"),
            )
            for p in photos
        ]

    @property
    def videos(self) -> Optional[list[Video]]:
        """
        Video attached to the listing, if any.

        :return: :class:`Video` or ``None``.
        :rtype: Video or None
        """

        if self._field("videos") is None:
            return None

        videos = self._field("videos", default=[])
        return [
            Video(
                id=v.get("id"),
                thumbnail_image_url=v.get("thumbnail_image_url"),
                video_url=v.get("video_url"),
            )
            for v in videos
        ]

    # ---------- seller ----------

    @property
    def seller(self) -> Optional[Seller]:
        """
        Return the Facebook Marketplace seller of the listing.

        Returns ``None`` for partner listings, where seller information is
        represented by :attr:`partner_seller` instead.

        :return: Seller information, or ``None`` when unavailable or when
            the listing is a partner listing.
        :rtype: Seller or None
        """

        if self._field("product_details_type") == "PARTNER_LISTING":
            return None

        seller_data = self._field("seller")
        if not seller_data:
            return None

        # PDP shape: {profile: {...}, seller_stats: {...}, ...}
        if "profile" in seller_data:
            profile_data = seller_data.get("profile") or {}
            seller_stats = seller_data.get("seller_stats") or {}
            combined_stats = seller_data.get("seller_buyer_combined") or {}

            return Seller(
                profile=Profile(
                    self._context,
                    {
                        "id": profile_data.get("id"),
                        "name": profile_data.get("name"),
                        "profile_picture_url": profile_data.get("profile_picture_url"),
                    },
                ),
                is_verified=seller_data.get("verified_badge"),
                seller_ratings_average=seller_stats.get("five_star_ratings_average"),
                seller_ratings_count=seller_stats.get(
                    "five_star_total_rating_count_by_role"
                ),
                seller_ratings_are_private=seller_data.get(
                    "seller_ratings_are_private"
                ),
                combined_ratings_average=combined_stats.get(
                    "five_star_ratings_average"
                ),
                combined_ratings_count=combined_stats.get(
                    "five_star_total_rating_count_by_role"
                ),
                combined_ratings_are_private=seller_data.get(
                    "seller_buyer_combined_ratings_are_private"
                ),
            )

        return Seller(
            profile=Profile(
                self._context,
                {
                    "id": seller_data.get("id"),
                    "name": seller_data.get("name"),
                    "profile_picture_url": seller_data.get("profile_picture_url"),
                },
            ),
        )

    @property
    def partner_seller(self) -> Optional[PartnerSeller]:
        """
        Return the partner marketplace seller of the listing.

        Returns ``None`` when the listing is not a partner listing.

        :return: Partner seller information, or ``None`` when unavailable
            or when the listing is not a partner listing.
        :rtype: PartnerSeller or None
        """

        if self._field("product_details_type") != "PARTNER_LISTING":
            return None

        partner_data = self._field("partner")
        if not partner_data:
            return None

        profile_data = partner_data.get("profile") or {}

        return PartnerSeller(
            profile=Profile(
                self._context,
                {
                    "id": profile_data.get("id"),
                    "name": profile_data.get("name"),
                    "profile_picture_url": profile_data.get("profile_picture_url"),
                },
            ),
            partner_brand_name=partner_data.get("partner_brand_name"),
            seller_review_count=partner_data.get("seller_review_count"),
            seller_positive_ratings_pct=partner_data.get("seller_positive_ratings_pct"),
            seller_member_since=partner_data.get("seller_member_since"),
            number_of_sold_listings=partner_data.get("number_of_sold_listings"),
            average_ship_time=partner_data.get("average_ship_time"),
        )

    # ---------- factory ----------

    @classmethod
    def from_listing_id(
        cls,
        context: FacebookContext,
        listing_id: str,
    ) -> "MarketplaceListing":
        """
        Create a marketplace listing from its Facebook ID.
        Automatically fetches full listing metadata.

        :param context: Facebook context used to fetch the listing.
        :type context: FacebookContext
        :param listing_id: Facebook listing ID.
        :type listing_id: str
        :return: Listing with metadata fetched.
        :rtype: MarketplaceListing
        """
        listing = cls(context, {"id": listing_id})
        listing._obtain_metadata()
        return listing


class SearchEngine:
    """
    Facebook search service.

    :param context: Facebook context used for GraphQL requests.
    :type context: FacebookContext
    """

    def __init__(self, context: FacebookContext):
        self._context = context

    @overload
    def search(
        self, text: str, filter_type: Literal["profile"], exact_match: bool = ...
    ) -> PaginatedIterator[Profile]: ...
    @overload
    def search(
        self, text: str, filter_type: Literal["post"], exact_match: bool = ...
    ) -> PaginatedIterator[Post]: ...
    @overload
    def search(
        self, text: str, filter_type: Literal["group"], exact_match: bool = ...
    ) -> PaginatedIterator[Group]: ...
    @overload
    def search(
        self, text: str, filter_type: Literal["all"] = ..., exact_match: bool = ...
    ) -> PaginatedIterator[Profile | Post | Group]: ...

    def search(self, text, filter_type="all", exact_match=False):
        """
        Search Facebook for profiles, posts, and groups.

        :param text: Search text.
        :type text: str
        :param filter_type: Result type to search for. Supported values are
            ``"all"``, ``"profile"``, ``"post"``, and ``"group"``.
        :type filter_type: str
        :param exact_match: Whether to return only exact matches.
        :type exact_match: bool
        :return: Iterator yielding Profile, Post, or Group objects.
        :rtype: PaginatedIterator
        """

        serp_graphql = SearchCometResultsPaginatedResultsQueryGraphQL(self._context)

        def request_fn(cursor):
            return serp_graphql.send(
                text=text,
                filter_type=filter_type,
                exact_match=exact_match,
                cursor=cursor,
            ).text

        def page_wrapper(parsed):
            raw = []
            for p in parsed["parsed_data"]["profiles"]:
                raw.append(
                    {
                        "type": "profile",
                        "data": {
                            "id": p["id"],
                            "name": p["name"],
                            "url": p["url"],
                            "profile_picture_url": p["profile_picture_url"],
                            "is_verified": p["is_verified"],
                        },
                    },
                )
            for p in parsed["parsed_data"]["posts"]:
                raw.append(
                    {
                        "type": "post",
                        "data": {
                            "id": p["id"],
                            "creation_time": p["creation_time"],
                            "url": p["url"],
                            "author": {
                                "type": p["author"]["type"],
                                "id": p["author"]["id"],
                                "name": p["author"]["name"],
                                "url": p["author"]["url"],
                            },
                        },
                    }
                )
            for g in parsed["parsed_data"]["groups"]:
                raw.append(
                    {
                        "type": "group",
                        "data": {
                            "id": g["id"],
                            "name": g["name"],
                            "url": g["url"],
                            "profile_picture_url": g["profile_picture_url"],
                        },
                    }
                )
            return raw, parsed["parsed_data"]["page_info"]

        def item_wrapper(raw):
            if raw["type"] == "profile":
                return Profile(self._context, raw["data"])
            if raw["type"] == "post":
                return Post(self._context, raw["data"])
            if raw["type"] == "group":
                return Group(self._context, raw["data"])

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="serp_search",
            query_variables={
                "text": text,
                "filter_type": filter_type,
                "exact_match": exact_match,
            },
        )

    def search_marketplace(
        self,
        query: str,
        *,
        is_stock_available: bool = True,
        filter_location_latitude: float = 40.7128,
        filter_location_longitude: float = -74.0060,
        filter_price_lower_bound: int = 0,
        filter_price_upper_bound: int = 2147483647,
        filter_radius_km: int = 500,
        item_condition: str = None,
        last_n_days: int = None,
        sort_by: str = None,
    ) -> PaginatedIterator[MarketplaceListing]:
        """
        Search Facebook Marketplace listings.

        Yields :class:`MarketplaceListing` objects lazily, paginating
        through the Marketplace search GraphQL endpoint.

        :param query: Search text.
        :type query: str
        :param is_stock_available: Filter to listings currently in stock.
        :type is_stock_available: bool
        :param filter_location_latitude: Latitude to center the search radius on.
        :type filter_location_latitude: float or None
        :param filter_location_longitude: Longitude to center the search radius on.
        :type filter_location_longitude: float or None
        :param filter_price_lower_bound: Minimum price, in the listing's currency.
        :type filter_price_lower_bound: int or None
        :param filter_price_upper_bound: Maximum price, in the listing's currency.
        :type filter_price_upper_bound: int or None
        :param filter_radius_km: Search radius in kilometres.
        :type filter_radius_km: int or None
        :param item_condition: Listing condition, one of ``"new"``,
            ``"used_like_new"``, ``"used_good"``, ``"used_fair"``.
        :type item_condition: str or None
        :param last_n_days: Restrict results to listings created within
            the last ``N`` days (includes today).
        :type last_n_days: int or None
        :param sort_by: Sort order, one of ``"CREATION_TIME_DESCEND"``,
            ``"PRICE_DESCEND"``, ``"PRICE_ASCEND"``, ``"DISTANCE_ASCEND"``.
        :type sort_by: str or None
        :return: Iterator yielding :class:`MarketplaceListing` objects.
        :rtype: PaginatedIterator
        """
        marketplace_search_graphql = CometMarketplaceSearchContentPaginationQueryGraphQL(
            self._context
        )

        def request_fn(cursor):
            return marketplace_search_graphql.send(
                query=query,
                cursor=cursor,
                is_stock_available=is_stock_available,
                filter_location_latitude=filter_location_latitude,
                filter_location_longitude=filter_location_longitude,
                filter_price_lower_bound=filter_price_lower_bound,
                filter_price_upper_bound=filter_price_upper_bound,
                filter_radius_km=filter_radius_km,
                item_condition=item_condition,
                last_n_days=last_n_days,
                sort_by=sort_by,
            ).text

        def page_wrapper(parsed):

            raw_items = [
                {
                    "id": listing["id"],
                    "title": listing["title"],
                    "category_id": listing["category_id"],
                    "currency": listing["currency"],
                    "price": listing["price"],
                    "strikethrough_price": listing["strikethrough_price"],
                    "location_text": f"{listing['location']['city']}, {listing['location']['state']}",
                    "is_hidden": listing["is_hidden"],
                    "is_live": listing["is_live"],
                    "is_pending": listing["is_pending"],
                    "is_sold": listing["is_sold"],
                    "created_with_seller_app": listing["created_with_seller_app"],
                    "delivery_types": listing["delivery_types"],
                    "seller": {
                        "profile": {
                            "id": listing["seller"]["profile"]["id"],
                            "name": listing["seller"]["profile"]["name"],
                        },
                    },
                    "photos": [
                        {
                            "id": listing["listing_photo"]["id"],
                            "image_url": listing["listing_photo"]["image_url"],
                        }
                    ]
                    if listing["listing_photo"]
                    else [],
                    "videos": [{"id": listing["video"]["id"]}]
                    if listing["video"]
                    else [],
                }
                for listing in parsed["parsed_data"]["listings"]
            ]
            page_info = {
                "has_next_page": parsed["parsed_data"]["page_info"]["has_next_page"],
                "end_cursor": parsed["parsed_data"]["page_info"]["end_cursor"],
            }
            return raw_items, page_info

        def item_wrapper(raw):
            return MarketplaceListing(self._context, raw)

        return PaginatedIterator(
            request_fn=request_fn,
            parser=self._context.parse_graphql_response,
            page_wrapper=page_wrapper,
            item_wrapper=item_wrapper,
            iterator_type="marketplace_search",
            query_variables={
                "query": query,
                "is_stock_available": is_stock_available,
                "filter_location_latitude": filter_location_latitude,
                "filter_location_longitude": filter_location_longitude,
                "filter_price_lower_bound": filter_price_lower_bound,
                "filter_price_upper_bound": filter_price_upper_bound,
                "filter_radius_km": filter_radius_km,
                "item_condition": item_condition,
                "last_n_days": last_n_days,
                "sort_by": sort_by,
            },
        )
