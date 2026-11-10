from typing import Optional, Literal, Union, List, Dict, Any, Annotated
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ---------- pagination ----------

class ParserPageInfo(_Base):
    type_cursor: Optional[str] = None
    end_cursor: Optional[str] = None
    has_next_page: bool = False


# ---------- profile (with collections) ----------

class ParserCollectionEntry(_Base):
    id: Optional[str] = None
    collections: Dict[str, Optional[str]] = Field(default_factory=dict)


class ParserProfileTabs(_Base):
    About: Optional[ParserCollectionEntry] = None
    Followers: Optional[ParserCollectionEntry] = None
    Friends: Optional[ParserCollectionEntry] = None
    Photos: Optional[ParserCollectionEntry] = None
    Reels: Optional[ParserCollectionEntry] = None


class ParserAboutItemEntry(_Base):
    title: Optional[str] = None
    text: Optional[str] = None
    item: List[str] = Field(default_factory=list)


class ParserAboutSection(_Base):
    category: Optional[str] = None
    items: List[ParserAboutItemEntry] = Field(default_factory=list)


class ParserAboutCollection(_Base):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",            # keep unknown future Facebook section keys
    )

    directory_basic_info: Optional[ParserAboutSection] = None
    directory_bio: Optional[ParserAboutSection] = None
    directory_specialties: Optional[ParserAboutSection] = None
    directory_intro: Optional[ParserAboutSection] = None
    directory_category: Optional[ParserAboutSection] = None
    directory_personal_details: Optional[ParserAboutSection] = None
    directory_links: Optional[ParserAboutSection] = None
    directory_communities: Optional[ParserAboutSection] = None
    directory_offers: Optional[ParserAboutSection] = None
    directory_work: Optional[ParserAboutSection] = None
    directory_education: Optional[ParserAboutSection] = None
    directory_activites: Optional[ParserAboutSection] = None
    directory_interests: Optional[ParserAboutSection] = None
    directory_travel: Optional[ParserAboutSection] = None
    directory_contact_info: Optional[ParserAboutSection] = None
    directory_privacy_and_legal_info: Optional[ParserAboutSection] = None
    directory_names: Optional[ParserAboutSection] = None
    directory_rating_and_reviews: Optional[ParserAboutSection] = None
    directory_business_address: Optional[ParserAboutSection] = None
    directory_business_hours: Optional[ParserAboutSection] = None
    description: Optional[ParserAboutSection] = None

class ParserProfileRef(_Base):
    type: Literal["profile"] = "profile"
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_verified: Optional[bool] = None
    gender: Optional[str] = None
    alternate_name: Optional[str] = None
    status_text: Optional[str] = None
    followers_count: Optional[str] = None
    followees_count: Optional[str] = None
    friends_count: Optional[str] = None
    tabs: Optional[ParserProfileTabs] = None
    about: Optional[Dict[str, ParserAboutSection]] = None


# ---------- group ----------

class ParserGroup(_Base):
    type: Literal["group"] = "group"
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    member_count: Optional[Union[int, str]] = None
    creation_time: Optional[int] = None
    description: Optional[str] = None
    privacy_info: Optional[str] = None
    discoverability_info: Optional[str] = None
    sample_members: List[ParserProfileRef] = Field(default_factory=list)


class ParserGroupMember(_Base):
    type: Literal["group_member"] = "group_member"
    join_status: Optional[str] = None
    contribution_score: Optional[str] = None
    account: Optional[ParserProfileRef] = None


# ---------- media ----------

class ParserMediaBase(_Base):
    pass


class ParserPhotoMedia(ParserMediaBase):
    type: Literal["photo"] = "photo"
    id: str
    creation_time: Optional[int] = None
    image_url: Optional[str] = None


class ParserVideoMedia(ParserMediaBase):
    type: Literal["video"] = "video"
    id: Optional[str] = None
    length_in_second: Optional[float] = None
    creation_time: Optional[int] = None
    thumbnail_image_url: Optional[str] = None
    fallback_image_url: Optional[str] = None
    video_url: Optional[str] = None
    play_count: Optional[str] = None


class ParserGenericMedia(ParserMediaBase):
    type: Literal["genericMedia"] = "genericMedia"
    id: Optional[str] = None


class ParserExternalLink(ParserGenericMedia):
    type: Literal["genericMediaExtLink"] = "genericMediaExtLink"
    web_link: Optional[str] = None

class ParserAnimatedImage(ParserGenericMedia):
    type: Literal["genericMediaAnimatedImage"] = "genericMediaAnimatedImage"
    image_url: Optional[str] = None
    genericMedia_url: Optional[str] = None
    animated_image_attribution: Optional[str] = None

class ParserStickerMedia(ParserMediaBase):
    type: Literal["sticker"] = "sticker"
    id: Optional[str] = None
    label: Optional[str] = None
    image_url: Optional[str] = None


ParserMedia = Annotated[
    Union[ParserPhotoMedia, ParserVideoMedia, ParserGenericMedia, ParserExternalLink, ParserAnimatedImage, ParserStickerMedia],
    Field(discriminator="type"),
]


# ---------- post ----------

class ParserPostBase(_Base):
    id: str
    url: Optional[str] = None
    text: Optional[str] = None
    author: Optional[ParserProfileRef] = None
    reaction_count: Optional[int] = None
    reactors_visible: Optional[bool] = None
    comments_count: Optional[int] = None
    share_count: Optional[int] = None
    creation_time: Optional[int] = None
    group_id: Optional[str] = None

class ParserMediaPost(ParserPostBase):
    type: Literal["media_post"] = "media_post"
    media: Union[ParserPhotoMedia, ParserVideoMedia]
    nextMediaAfterNodeId: Optional[str] = None
    parent_post_id: Optional[str] = None
    
class ParserPost(ParserPostBase):
    type: Literal["post"] = "post"
    title: Optional[str] = None
    media_posts_count: Optional[int] = None
    media_posts: List[ParserMediaPost] = Field(default_factory=list)
    attachments: List[Union[ParserGenericMedia, ParserExternalLink, ParserAnimatedImage, ParserStickerMedia]] = Field(default_factory=list)

ParserFeedPost = Annotated[
    Union[ParserPost, ParserMediaPost],
    Field(discriminator="type"),
]

# ---------- reactor / comment ----------

class ParserReactor(_Base):
    type: Literal["reactor"] = "reactor"
    reaction_type_id: Optional[str] = None
    author: Optional[ParserProfileRef] = None


class ParserComment(_Base):
    type: Literal["comment"] = "comment"
    id: str
    text: Optional[str] = None
    attachments: List[ParserMedia] = Field(default_factory=list)
    creation_time: Optional[int] = None
    reaction_count: Optional[int] = None
    reply_count: Optional[int] = None
    reply_expansion_token: Optional[str] = None
    author: Optional[ParserProfileRef] = None
    post_id: Optional[str] = None
    parent_comment: Optional["ParserComment"] = None


ParserMediaPost.model_rebuild()
ParserPost.model_rebuild()
ParserComment.model_rebuild()

# ---------- collections ----------

ParserCollectionItem = Annotated[
    Union[ParserProfileRef, ParserMediaPost],
    Field(discriminator="type"),
]


# ---------- serp search ----------

class ParserSearchResults(_Base):
    type: Literal["search_results"] = "search_results"
    profiles: List[ParserProfileRef] = Field(default_factory=list)
    posts: List[ParserFeedPost] = Field(default_factory=list)
    groups: List[ParserGroup] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


# ---------- marketplace ----------

class ParserAttribute(_Base):
    name: Optional[str] = None
    value: Optional[Any] = None


class ParserMarketplaceCityPage(_Base):
    id: Optional[str] = None
    display_name: Optional[str] = None


class ParserMarketplaceLocation(_Base):
    city: Optional[str] = None
    state: Optional[str] = None
    city_page: Optional[ParserMarketplaceCityPage] = None


class ParserSellerStats(_Base):
    five_star_ratings_average: Optional[float] = None
    five_star_total_rating_count_by_role: Optional[int] = None


class ParserSeller(_Base):
    profile: Optional[ParserProfileRef] = None
    verified_badge: Optional[bool] = None
    seller_ratings_are_private: Optional[bool] = None
    seller_stats: ParserSellerStats = Field(default_factory=ParserSellerStats)
    seller_buyer_combined_ratings_are_private: Optional[bool] = None
    seller_buyer_combined: ParserSellerStats = Field(default_factory=ParserSellerStats)
    joined_time: Optional[int] = None


class ParserPartnerSeller(_Base):
    profile: Optional[ParserProfileRef] = None
    partner_brand_name: Optional[str] = None
    seller_review_count: Optional[int] = None
    seller_positive_ratings_pct: Optional[float] = None
    seller_member_since: Optional[int] = None
    number_of_sold_listings: Optional[int] = None
    average_ship_time: Optional[str] = None


class ParserMarketplaceListing(_Base):
    type: Literal["marketplace_listing"] = "marketplace_listing"
    id: str
    title: Optional[str] = None
    category_id: Optional[str] = None
    url: Optional[str] = None
    post_id: Optional[str] = None
    creation_time: Optional[int] = None
    currency: Optional[str] = None
    price: Optional[float] = None
    strikethrough_price: Optional[float] = None
    location: Optional[ParserMarketplaceLocation] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    discounts_text: Optional[str] = None
    is_live: Optional[bool] = None
    is_pending: Optional[bool] = None
    is_sold: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_on_marketplace: Optional[bool] = None
    min_listing_price: Optional[float] = None
    max_listing_price: Optional[float] = None
    delivery_types: Optional[List[str]] = None
    is_shipping_offered: Optional[bool] = None
    is_buy_now_enabled: Optional[bool] = None
    is_checkout_enabled: Optional[bool] = None
    is_cart_enabled: Optional[bool] = None
    is_purchase_protected: Optional[bool] = None
    inventory_count: Optional[int] = None
    messaging_enabled: Optional[bool] = None
    created_with_seller_app: Optional[bool] = None
    product_details_type: Optional[str] = None
    attributes: List[ParserAttribute] = Field(default_factory=list)
    listing_photo: Optional[ParserPhotoMedia] = None
    video: Optional[ParserVideoMedia] = None
    photos: List[ParserPhotoMedia] = Field(default_factory=list)
    videos: List[ParserVideoMedia] = Field(default_factory=list)
    seller: Optional[ParserSeller] = None
    partner: Optional[ParserPartnerSeller] = None
    shipping_cost_text: Optional[str] = None
    has_shipping_cost: Optional[bool] = None
    delivery_window_text: Optional[str] = None
    product_details_page_uri: Optional[str] = None


class ParserMarketplaceSearchPage(_Base):
    type: Literal["marketplace_search_page"] = "marketplace_search_page"
    listings: List[ParserMarketplaceListing] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


class ParserMarketplacePDP(_Base):
    type: Literal["marketplace_pdp"] = "marketplace_pdp"
    listing: ParserMarketplaceListing


class ParserMarketplaceMedia(_Base):
    type: Literal["marketplace_pdp_media"] = "marketplace_pdp_media"
    listing_id: Optional[str] = None
    is_hidden: Optional[bool] = None
    photos: List[ParserPhotoMedia] = Field(default_factory=list)
    videos: List[ParserVideoMedia] = Field(default_factory=list)


# ---------- pages ----------

class ParserCollectionPage(_Base):
    type: Literal["collection_page"] = "collection_page"
    collection_id: Optional[str] = None
    items: List[ParserCollectionItem] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


class ParserTimelinePage(_Base):
    type: Literal["timeline_page"] = "timeline_page"
    feeds: List[ParserFeedPost] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


class ParserReactorsPage(_Base):
    type: Literal["reactors_page"] = "reactors_page"
    post_id: Optional[str] = None
    reactors: List[ParserReactor] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)
    parent_comment_id: Optional[str] = None


class ParserCommentsPage(_Base):
    type: Literal["comments_page"] = "comments_page"
    comments: List[ParserComment] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


class ParserRepliesPage(_Base):
    type: Literal["replies_page"] = "replies_page"
    replies: List[ParserComment] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)


class ParserGroupMembersPage(_Base):
    type: Literal["group_members_page"] = "group_members_page"
    members: List[ParserGroupMember] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)

class ParserMediaPostsPage(_Base):
    type: Literal["media_posts_page"] = "media_posts_page"
    media_posts: List[ParserMediaPost] = Field(default_factory=list)
    page_info: ParserPageInfo = Field(default_factory=ParserPageInfo)

class ParsedResponse(_Base):
    type: Literal["parsed_response"] = "parsed_response"
    operation: Optional[str] = None
    parsed_data: Optional[Any] = None


