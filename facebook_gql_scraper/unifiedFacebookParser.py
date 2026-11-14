import json
import base64
from pydantic import BaseModel
from typing import Optional, List

import iso4217parse
from price_parser import Price

from .parserModels import *
# Fixed schema keys grouped by tab name
FIXED_TABS_SCHEMA = {
    "About": [
        "directory_basic_info", "directory_specialties", "directory_intro",
        "directory_category", "directory_personal_details", "directory_links",
        "directory_communities", "directory_offers", "directory_work",
        "directory_education", "directory_activites", "directory_interests",
        "directory_travel", "directory_contact_info",
        "directory_privacy_and_legal_info", "directory_names",
    ],
    "Followers": [
        "followers", "followers_mutual", "following", "following_mutual",
        "friends_all", "friends_mutual",
    ],
    "Friends": [
        "friends_all", "friends_mutual", "friends_recent",
        "friends_with_upcoming_birthdays", "friends_work", "friends_college",
        "friends_high_school", "friends_current_city", "friends_hometown",
        "followers", "following", "followers_mutual", "following_mutual",
    ],
    "Photos": ["photos_by", "photos_albums", "photos_of"],
    "Reels": ["owner_reels"],
}

###############
def _parse_comment_attachments(attachments: list) -> list[ParserMedia]:
    out: list[ParserMedia] = []
    for att in attachments or []:
        node = att.get("style_type_renderer") or {}
        inner = node.get("attachment") or {}
        # normalize the path so _parse_node_media sees the GraphQL shape
        media = _parse_node_media({
            "media": inner.get("media"),
            "style_type_renderer": node,
            "story_attachment_link_renderer": inner.get("story_attachment_link_renderer"),
        })
        if media is not None:
            out.append(media)
    return out

# ---------- ParserMedia -> ParserMediaPost ----------

def _wrap_media_post(
    media: ParserMedia,
    parent_post_id: Optional[str],
    *,
    url: Optional[str] = None,
    creation_time: Optional[int] = None,
    text: Optional[str] = None,
    author: Optional[ParserProfileRef] = None,
    reaction_count: Optional[int] = None,
    reactors_visible: Optional[bool] = None,
    comments_count: Optional[int] = None,
    share_count: Optional[int] = None,
    group_id: Optional[str] = None,
) -> ParserMediaPost:
    """Wrap a ParserMedia in a ParserMediaPost."""
    return ParserMediaPost(
        id=media.id or "",
        media=media,                       # NOTE: only Photo/Video are allowed by ParserMediaPost
        parent_post_id=parent_post_id,
        url=url,
        creation_time=creation_time or getattr(media, "creation_time", None),
        text=text,
        author=author,
        reaction_count=reaction_count,
        reactors_visible=reactors_visible,
        comments_count=comments_count,
        share_count=share_count,
        group_id=group_id,
    )


# ---------- GraphQL node -> ParserMedia model ----------

def _parse_node_media(node: dict) -> Optional[ParserMedia]:
    """Convert one GraphQL attachment node into a ParserMedia model.

    Handles photo, video (both lightweight and grid renderers), animated
    image, external link, and sticker. Returns None for unknown types.
    """
    if not node:
        return None

    media = node.get("media")
    if media is None:
        return None

    typename = media.get("__typename")

    if typename == "Photo":
        image_url = (
            (media.get("image") or {}).get("uri")
            or (media.get("photo_image") or {}).get("uri")
        )
        return ParserPhotoMedia(
            id=media.get("id"),
            image_url=image_url,
            creation_time=media.get("created_time"),
        )

    if typename == "Video":
        video = (media.get("video_grid_renderer") or {}).get("video") or media

        video_url = None
        for item in (
            (video.get("videoDeliveryResponseFragment") or {})
            .get("videoDeliveryResponseResult", {})
            .get("progressive_urls", [])
        ):
            if item.get("failure_reason") is None:
                video_url = item.get("progressive_url")
                break

        thumb = (
            (video.get("preferred_thumbnail") or {}).get("image", {}).get("uri")
            or (media.get("preferred_thumbnail") or {}).get("image", {}).get("uri")
        )

        if video.get("playable_duration_in_ms"):
            length = round(video["playable_duration_in_ms"] / 1000, 1)
        else:
            length = media.get("length_in_second")

        return ParserVideoMedia(
            id=media.get("id"),
            video_url=video_url,
            thumbnail_image_url=thumb,
            length_in_second=length,
            creation_time=media.get("created_time"),
        )

    if typename == "GenericAttachmentMedia":
        renderer = (node.get("style_type_renderer") or {}).get("__typename")
        if renderer == "StoryAttachmentAnimatedImageShareStyleRenderer":
            return ParserAnimatedImage(
                id=media.get("id"),
                image_url=(media.get("image") or {}).get("uri"),
                genericMedia_url=(media.get("animated_image") or {}).get("uri"),
                animated_image_attribution=media.get("animated_image_attribution"),
            )
        # external link share
        web_link = (
            ((node.get("story_attachment_link_renderer") or {})
             .get("attachment") or {})
            .get("web_link", {}).get("url")
        )
        return ParserExternalLink(id=media.get("id"), web_link=web_link)

    if typename == "Sticker":
        return ParserStickerMedia(
            id=media.get("id"),
            label=media.get("label"),
            image_url=(media.get("image") or {}).get("uri"),
        )

    return None


def _parse_post_attachments(attachments: list) -> tuple[list[ParserMediaPost], list[ParserMedia], int]:
    """Return (media_posts, non_media_attachments, media_posts_count)."""
    media_posts: list[ParserMediaPost] = []
    non_media_post: list[ParserMedia] = []
    count = 0

    for att in attachments or []:
        styles = att.get("styles") or {}
        style_type = styles.get("__typename")

        if style_type in (
            "StoryAttachmentAlbumStyleRenderer",
            "StoryAttachmentAlbumFrameStyleRenderer",
        ):
            sub = (
                (styles.get("attachment") or {}).get("all_subattachments")
                or (styles.get("attachment") or {}).get("frame_sublayout_subattachments")
                or {}
            )
            count += sub.get("count") or 0
            for node in sub.get("nodes", []):
                media = _parse_node_media(node)
                _dispatch(media, media_posts, non_media_post)

        elif style_type == "StoryAttachmentFBReelsStyleRenderer":
            for info in (styles.get("attachment") or {}).get("style_infos", []):
                for inner in (info.get("fb_shorts_story") or {}).get("attachments", []) or []:
                    before = len(media_posts)
                    media = _parse_node_media(inner)
                    _dispatch(media, media_posts, non_media_post)
                    count += len(media_posts) - before

        else:
            before = len(media_posts)
            media = _parse_node_media(styles.get("attachment") or {})
            _dispatch(media, media_posts, non_media_post)
            count += len(media_posts) - before

    return media_posts, non_media_post, count


def _dispatch(media, media_posts, non_media):
    if media is None:
        return
    if isinstance(media, (ParserPhotoMedia, ParserVideoMedia)):
        media_posts.append(_wrap_media_post(media, parent_post_id=None))
    else:
        non_media.append(media)

def _parse_reactions_from_ufi(target):
    """
    Parse reaction count, display strategy, and share count from a feedback target.

    Returns (reactions_dict, reaction_display_strategy, share_count).
    """
    reactions = {"total": None, "breakdown": []}
    reaction_display_strategy = None
    share_count = None
    fb = target.get("comet_ufi_summary_and_actions_renderer", {}).get("feedback", {})

    # Total reaction count + share count
    for action in fb.get("adaptive_ufi_action_renderers", []):
        if action.get("__typename") == "UFIStoryReactActionRenderer":
            reactions["total"] = (
                action.get("feedback", {}).get("reaction_count", {}).get("count", None)
            )
            reaction_display_strategy = (
                action.get("feedback", {})
                .get("reaction_display_config", {})
                .get("reaction_display_strategy", None)
            )
        elif action.get("__typename") == "XFBUFIAdaptiveShareActionRenderer":
            share_count = (
                action.get("feedback", {}).get("share_count", {}).get("count", None)
            )

    # Reaction breakdown (Like, Love, Care, etc.)
    for edge in fb.get("top_reactions", {}).get("edges", []):
        reaction_id = edge.get("node", {}).get("id")
        name = edge.get("node", {}).get("localized_name")
        count = edge.get("reaction_count", None)
        if name:
            reactions["breakdown"].append(
                {"id": reaction_id, "name": name, "count": count}
            )

    return reactions, reaction_display_strategy, share_count


def _get_comments_count(node):
    """Extract the comment total_count from a feed node's comet_sections."""
    return (
        node.get("comet_sections", {})
        .get("feedback", {})
        .get("story", {})
        .get("story_ufi_container", {})
        .get("story", {})
        .get("feedback_context", {})
        .get("feedback_target_with_context", {})
        .get("comment_rendering_instance", {})
        .get("comments", {})
        .get("total_count", None)
    )


# ---------- feed post -> list[ParserFeedPost] ----------

def _parse_feed_post(edge) -> list[ParserFeedPost]:
    """Build a ParserPost from a feed edge (user timeline or group feed)."""
    node = edge.get("node", {})

    post_id = node.get("post_id")
    if not post_id:
        return []

    ufi_container = (
        node.get("comet_sections", {})
        .get("feedback", {})
        .get("story", {})
        .get("story_ufi_container", {})
        .get("story", {})
    )

    shareable = ufi_container.get("shareable_from_perspective_of_feed_ufi") or {}
    shareable_typename = shareable.get("__typename")
    # "Photo" | "Video" | "Album" | "Story" | None

    media_posts, non_media_post, media_posts_count = _parse_post_attachments(node.get("attachments", []))

    # set parent_post_id on every wrapped media post
    for mp in media_posts:
        mp.parent_post_id = post_id
        
    if shareable_typename != "Story":
        return media_posts


    target = ufi_container.get("feedback_context", {}).get(
        "feedback_target_with_context", {}
    )
    
    reactions, reaction_display_strategy, share_count = _parse_reactions_from_ufi(
        target
    )
    comments_count = _get_comments_count(node)

    comet_story_layout = (
        node.get("comet_sections", {}).get("context_layout", {}).get("story", {})
    )
    title_text = None
    title = (
        comet_story_layout.get("comet_sections", {})
        .get("title", {})
        .get("story", {})
        .get("title", None)
    )
    if title is not None:
        title_text = title.get("text", None)

    comet_story = node.get("comet_sections", {}).get("content", {}).get("story", {})
    text = None
    if comet_story.get("message", None) is not None:
        text = comet_story.get("message", {}).get("text", None)

    return [
        ParserPost(
            id=post_id,
            creation_time=node.get("creation_time"),
            url=(node.get("comet_sections", {}).get("content", {}).get("story", {}) or {}).get("wwwURL"),
            author=ParserProfileRef(
                id=(node.get("actors") or [{}])[0].get("id"),
                name=(node.get("actors") or [{}])[0].get("name"),
                url=(node.get("actors") or [{}])[0].get("url"),
            ),
            title=title_text,
            text=text,
            attachments=non_media_post,
            reaction_count=reactions["total"],
            reactors_visible=(reaction_display_strategy == "NONE") if reaction_display_strategy else None,
            share_count=share_count,
            comments_count=comments_count,
            media_posts_count=media_posts_count,
            media_posts=media_posts,
        )
    ]



def _parse_timeline_feed(data, feed_key) -> ParserTimelinePage:
    """
    Parse a feed of posts from a user timeline or group timeline.
    feed_key: "timeline_list_feed_units" (user) or "group_feed" (group).
    """
    candidates = [data.get("data", {}).get("node", {}), data.get("node", {})]

    # Aggregate edges from any candidate containing feed edges
    all_edges = []
    for entity in candidates:
        edges = entity.get(feed_key, {}).get("edges", [])
        if edges:
            all_edges.extend(edges)

    # Locate page_info across candidates (handles detached root page_info)
    raw_page_info = {}
    for entity in candidates:
        info = entity.get(feed_key, {}).get("page_info", {})
        if info:
            raw_page_info = info
            break

    feeds = []
    for edge in all_edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue
        feeds.extend(_parse_feed_post(edge))


    return ParserTimelinePage(
        feeds=feeds,
        page_info=ParserPageInfo(
            type_cursor="feeds",
            end_cursor=raw_page_info.get("end_cursor"),
            has_next_page=raw_page_info.get("has_next_page", False),
        ),
    )


def _extract_group_from_view_model(vm) -> Optional[ParserGroup]:
    """Build a normalized group dict from a SearchProfileViewModel."""
    profile = vm.get("profile")
    if not profile or profile.get("__typename") != "Group":
        return None

    return ParserGroup(
        id=profile.get("id"),
        name=profile.get("name"),
        url=profile.get("url") or profile.get("profile_url"),
        profile_picture_url=profile.get("profile_picture", {}).get("uri"),
    )


def parse_profile_collection_ids(data: dict) -> ParserProfileRef:
    """Parse a profile header payload into a ParserProfileRef with tabs."""

    user = (
        data.get("data", {})
        .get("user", {})
        .get("profile_header_renderer", {})
        .get("user", {})
    )

    # Author Profile Extraction
    status_text = (
        user.get("profile_status", {}).get("profile_status_text", {}).get("text")
        if user.get("profile_status")
        else None
    )

    followers_count = None
    followees_count = None
    friends_count = None

    for content in (user.get("profile_social_context") or {}).get("content", []):
        text = content.get("text", {}).get("text")
        if text.endswith("friends"):
            friends_count = text.removesuffix("friends").strip()
        if text.endswith("followers"):
            followers_count = text.removesuffix("followers").strip()
        if text.endswith("following"):
            followees_count = text.removesuffix("following").strip()
    # Initialize Tab structure with default None for section ID and collections
    parsed_tabs = {
        tab_name: {"id": None, "collections": {col_key: None for col_key in keys}}
        for tab_name, keys in FIXED_TABS_SCHEMA.items()
    }

    sections = (
        user.get("profile_tabs", {})
        .get("profile_user", {})
        .get("timeline_nav_app_sections", {})
        .get("edges", [])
    )

    for edge in sections:
        node = edge.get("node", {})
        tab_name = node.get("name")

        if tab_name in parsed_tabs:
            parsed_tabs[tab_name]["id"] = node.get("id")
            collections = node.get("all_collections", {}).get("nodes", [])
            for col in collections:
                col_key = col.get("tab_key")
                col_id = col.get("id")
                if col_key in parsed_tabs[tab_name]["collections"]:
                    parsed_tabs[tab_name]["collections"][col_key] = col_id

    return ParserProfileRef(
        id=user.get("id", None),
        name=user.get("name", None),
        alternate_name=user.get("alternate_name", None),
        gender=user.get("gender", None),
        url=user.get("url", None),
        status_text=status_text,
        profile_picture_url=user.get("profilePicLarge", {}).get("uri", None),
        is_verified=user.get("show_verified_badge_on_profile", None),
        followers_count=followers_count,
        followees_count=followees_count,
        friends_count=friends_count,
        tabs=ParserProfileTabs(
            About=ParserCollectionEntry(**parsed_tabs["About"]),
            Followers=ParserCollectionEntry(**parsed_tabs["Followers"]),
            Friends=ParserCollectionEntry(**parsed_tabs["Friends"]),
            Photos=ParserCollectionEntry(**parsed_tabs["Photos"]),
            Reels=ParserCollectionEntry(**parsed_tabs["Reels"]),
        ),
    )

def parse_about_collections(data: dict) -> ParserAboutCollection:
    """
    Extracts text contents specifically for 'About' tab section keys.
    """
    about_data: dict[str, ParserAboutSection] = {}

    about_nodes = (
        data.get("data", {})
        .get("user", {})
        .get("about_app_sections", {})
        .get("nodes", [])
    )

    for section in about_nodes:
        active_collections = section.get("activeCollections", {}).get("nodes", [])

        for col in active_collections:
            style_renderer = col.get("style_renderer") or {}
            profile_field_sections = style_renderer.get("profile_field_sections", [])

            for field_sec in profile_field_sections:
                result_items: List[ParserAboutItemEntry] = []
                sec_type = field_sec.get("field_section_type")
                category = field_sec.get("title", {}).get("text", None)

                profile_fields_nodes = field_sec.get("profile_fields", {}).get("nodes", [])
                for node in profile_fields_nodes:
                    title_text = (
                        node.get("title", {}).get("text") if node.get("title") else None
                    )
                    text_value = None
                    item_list: List[str] = []

                    for item in node.get("list_item_groups", []):
                        for subitem in item.get("list_items", []):
                            item_list.append(subitem.get("text").get("text", None))

                    if node.get("renderer") is not None:
                        text_content = (
                            node.get("renderer", {})
                            .get("field", {})
                            .get("text_content", None)
                        )
                        if text_content is not None:
                            text_value = text_content.get("text", None)

                        text_content2 = node.get("renderer", {}).get("text_content", None)
                        if text_content2 is not None:
                            text_value = text_content2.get("text", None)

                        for travel_item in node.get("renderer", {}).get("travel_profile_items", []):
                            travel_name = travel_item.get("page").get("name")
                            visit_time = travel_item.get("visit_time")
                            item_list.append(f"{travel_name}:{visit_time}")

                    result_items.append(
                        ParserAboutItemEntry(
                            title=title_text,
                            text=text_value,
                            item=item_list,
                        )
                    )

                if sec_type is not None:
                    about_data[sec_type] = ParserAboutSection(
                        category=category,
                        items=result_items,
                    )

    return ParserAboutCollection(**about_data)

def parse_post(data) -> ParserPost:
    """Parse a single-post dialog payload (`data.node_v2`) into a ParserPost."""

    # Navigate node_v2 directly via dictionary access
    node_v2 = data.get("data", {}).get("node_v2", {})
    post_id= node_v2.get("post_id", None)
    comet_story = node_v2.get("comet_sections", {}).get("content", {}).get("story", {})
    comet_story_layout = (
        node_v2.get("comet_sections", {}).get("context_layout", {}).get("story", {})
    )

    ufi_container = (
        node_v2.get("comet_sections", {})
        .get("feedback", {})
        .get("story", {})
        .get("story_ufi_container", {})
        .get("story", {})
    )
    target = ufi_container.get("feedback_context", {}).get(
        "feedback_target_with_context", {}
    )

    comment_data = (
        target.get("comment_list_renderer", {})
        .get("feedback", {})
        .get("comment_rendering_instance_for_feed_location", {})
        .get("comments", {})
    )

    reactions, reaction_display_strategy, share_count = _parse_reactions_from_ufi(
        target
    )

    media_posts, non_media_post, media_posts_count = _parse_post_attachments(node_v2.get("attachments", []))

    # set parent_post_id on every wrapped media post
    for mp in media_posts:
        mp.parent_post_id = post_id

    title_text = None
    title = (
        comet_story_layout.get("comet_sections", {})
        .get("title", {})
        .get("story", {})
        .get("title", None)
    )
    if title is not None:
        title_text = title.get("text", None)

    text = None
    if comet_story.get("message", None) is not None:
        text = comet_story.get("message", {}).get("text", None)

    group_id = None
    associated_group = node_v2.get("feedback").get("associated_group")
    if associated_group is not None:
        group_id=associated_group.get("id")

    return ParserPost(
        id=post_id,
        creation_time=node_v2.get("creation_time", None),
        url=comet_story.get("wwwURL", None),
        author=ParserProfileRef(
            id=comet_story.get("actors", [{}])[0].get("id", None),
            name=comet_story.get("actors", [{}])[0].get("name", None),
            url=comet_story.get("actors", [{}])[0].get("url", None),
            profile_picture_url=(
                comet_story.get("actors", [{}])[0]
                .get("profile_picture", {})
                .get("uri", None)
            ),
        ),
        title=title_text,
        text=text,
        attachments=non_media_post,
        reaction_count=reactions["total"],
        reactors_visible=(reaction_display_strategy == "NONE") if reaction_display_strategy else None,
        share_count=share_count,
        comments_count=comment_data.get("total_count", None),
        media_posts_count=media_posts_count,
        media_posts=media_posts,
        group_id=group_id,
        feedback_id=node_v2.get("feedback").get("id"),
    )

def parse_reactors(data) -> ParserReactorsPage:
    """Parse a reactors list response into a ParserReactorsPage."""

    node = data.get("data", {}).get("node", {})
    decoded = base64.b64decode(node.get("id")).decode("utf-8")
    feedback_id = decoded.split(":")[-1]

    post_id, comment_id = None, None
    if "_" in feedback_id:
        post_id, comment_id = feedback_id.split("_", 1)
    else:
        post_id = feedback_id

    reactors_conn = node.get("reactors", {})
    edges = reactors_conn.get("edges", [])
    raw_page_info = reactors_conn.get("page_info", {})

    reactors = []
    for edge in edges:
        user_node = edge.get("node", {})

        reactors.append(
            ParserReactor(
                reaction_type_id=edge.get("feedback_reaction_info", {}).get("id"),
                reaction_type=edge.get("feedback_reaction_info", {}).get("reaction_type"),
                author=ParserProfileRef(
                    id=user_node.get("id"),
                    name=user_node.get("name"),
                    url=user_node.get("profile_url"),
                    profile_picture_url=(user_node.get("profile_picture") or {}).get("uri"),
                ),
            )
        )

    return ParserReactorsPage(
        post_id=post_id,
        reactors=reactors,
        page_info=ParserPageInfo(
            type_cursor="reactors",
            has_next_page=raw_page_info.get("has_next_page", False),
            end_cursor=raw_page_info.get("end_cursor"),
        ),
        parent_comment_id=comment_id,
    )


def parse_facebook_comments(data) -> ParserCommentsPage:
    """Parse a comments pagination payload into a ParserCommentsPage."""

    # Safely traverse nested structure to reach comments array
    comments_data = (
        data.get("data", {})
        .get("node", {})
        .get("comment_rendering_instance_for_feed_location", {})
        .get("comments", {})
    )

    parsed_comments = []

    for edge in comments_data.get("edges", []):
        node = edge.get("node", {})
        if not node:
            continue

        decoded = base64.b64decode(node.get("id")).decode("utf-8")
        post_id, comment_id = decoded.split(":")[-1].split("_", 1)

        author = node.get("author", {})

        text = None
        body = node.get("body", None)
        if body:
            text = body.get("text", None)

        attachments = _parse_comment_attachments(node.get("attachments", []))

        parsed_comments.append(
            ParserComment(
                id=comment_id,
                text=text,
                attachments=attachments,
                creation_time=node.get("created_time"),
                reaction_count=(node.get("feedback", {}).get("reactors") or {}).get("count_reduced"),
                reply_count=(node.get("feedback", {}).get("replies_fields") or {}).get("total_count"),
                reply_expansion_token=(node.get("feedback", {}).get("expansion_info") or {}).get("expansion_token"),
                author=ParserProfileRef(
                    id=author.get("id"),
                    name=author.get("name"),
                    gender=author.get("gender"),
                    url=author.get("url"),
                    profile_picture_url=(author.get("profile_picture_depth_0") or {}).get("uri"),
                ),
                post_id=post_id,
                feedback_id=node.get("feedback").get("id"),
            )
        )
        
    return ParserCommentsPage(
        comments=parsed_comments,
        page_info=ParserPageInfo(
            type_cursor="comments",
            end_cursor=comments_data.get("page_info", {}).get("end_cursor"),
            has_next_page=comments_data.get("page_info", {}).get("has_next_page", False),
        ),
    )


def parse_comment_replies(data, comment_type="reply") -> ParserRepliesPage:
    """
    Parses comment replies payload from Facebook GraphQL response,
    including pagination cursor metadata.
    """

    node = data.get("data", {}).get("node", {})
    replies_conn = node.get("replies_connection", {})

    parsed_replies = []
    for edge in replies_conn.get("edges", []):
        reply_node = edge.get("node", {})
        if not reply_node:
            continue

        comment_direct_parent = reply_node.get("comment_direct_parent", {})

        reply_node_id_decoded = base64.b64decode(reply_node["id"]).decode("utf-8")
        post_id, comment_id = reply_node_id_decoded.split(":")[-1].split("_")

        comment_direct_parent_id_decoded = base64.b64decode(
            comment_direct_parent.get("id", {})
        ).decode("utf-8")
        _parent_post_id, parent_comment_id = comment_direct_parent_id_decoded.split(":")[
            -1
        ].split("_")

        text = None
        body = reply_node.get("body", None)
        if body:
            text = body.get("text", None)

        attachments = _parse_comment_attachments(node.get("attachments", []))

        comment = ParserComment(
            id=comment_id,
            text=text,
            attachments=attachments,
            creation_time=reply_node.get("created_time"),
            reaction_count=(
                reply_node.get("feedback", {})
                .get("reactors", {})
                .get("count_reduced")
            ),
            author=ParserProfileRef(
                id=reply_node.get("author", {}).get("id"),
                name=reply_node.get("author", {}).get("name"),
                gender=reply_node.get("author", {}).get("gender"),
                url=reply_node.get("author", {}).get("url"),
                profile_picture_url=(
                    reply_node.get("author", {})
                    .get("profile_picture_depth_0", {})
                    .get("uri")
                ),
            ),
            parent_comment=ParserComment(
                id=parent_comment_id,
                author=ParserProfileRef(
                    name=comment_direct_parent.get("author", {}).get("name"),
                    gender=comment_direct_parent.get("author", {}).get("gender"),
                ),
                feedback_id=node.get("id"),
            ),
            post_id=post_id,
            feedback_id=reply_node.get("feedback").get("id"),
        )

        if comment_type == "reply":
            comment.reply_count = (
                reply_node.get("feedback", {})
                .get("replies_fields", {})
                .get("total_count")
            )
            comment.reply_expansion_token = (
                reply_node.get("feedback", {})
                .get("expansion_info", {})
                .get("expansion_token")
            )

        parsed_replies.append(comment)

    return ParserRepliesPage(
        replies=parsed_replies,
        page_info=ParserPageInfo(
            type_cursor="comment_replies",
            end_cursor=replies_conn.get("page_info", {}).get("end_cursor"),
            has_next_page=replies_conn.get("page_info", {}).get("has_next_page", False),
        ),
    )


def parse_facebook_group_hovercard(data) -> ParserGroup:
    """Parse a group hovercard response into a ParserGroup."""

    node = data.get("data", {}).get("node", {})
    group = node.get("comet_hovercard_renderer", {}).get("group", {})

    # Extract sample members from the facepile list
    facepile_edges = group.get("facepile_profiles", {}).get("edges", [])
    sample_members = [
        ParserProfileRef(
            id=edge.get("node", {}).get("id"),
            name=edge.get("node", {}).get("name"),
            url=edge.get("node", {}).get("url"),
            profile_picture_url=(
                edge.get("node", {}).get("profile_picture", {}).get("uri")
            ),
        )
        for edge in facepile_edges
        if edge.get("node")
    ]

    return ParserGroup(
        id=group.get("id") or node.get("id"),
        name=group.get("name"),
        url=group.get("profile_url") or group.get("url"),
        member_count=group.get("group_member_profiles", {}).get("formatted_count_text"),
        profile_picture_url=group.get("profile_picture", {}).get("uri"),
        sample_members=sample_members,
    )



def parse_facebook_timeline(data) -> ParserTimelinePage:
    """Parse a user timeline feed into a ParserTimelinePage."""
    return _parse_timeline_feed(data, "timeline_list_feed_units")


def parse_group_about_info(data) -> ParserGroup:
    """Parse a group About payload into a ParserGroup."""

    group_data = data.get("data", {}).get("group", {})
    feed_units = group_data.get("about_feed_units", [])

    # Initialize with None — ParserGroup allows all optional fields
    group_id = group_data.get("id")
    creation_time = None
    member_count = None
    description = None
    privacy_info = None
    discoverability_info = None

    for unit in feed_units:
        typename = unit.get("__typename")
        unit_group = unit.get("group", {})

        # Fallback to unit-level ID if not present at the top level
        if not group_id and unit_group.get("id"):
            group_id = unit_group.get("id")

        # Description, Privacy, and Discoverability
        if typename == "GroupsAboutFeedAboutCardUnit":
            desc_entities = unit_group.get("description_with_entities", {})
            description = desc_entities.get("text")

            for item in unit_group.get("about_info_items", []):
                item_type = item.get("__typename")
                item_group = item.get("group", {})

                if item_type == "XFBPrivacyGroupsAboutInfoItem":
                    privacy_info = item_group.get("privacy_info").get("label").get("text")
                elif item_type == "XFBDiscoverabilityGroupsAboutInfoItem":
                    discoverability_info = item_group.get("discoverability_info").get("label").get("text")

        # Member count via formatted_count_text
        elif typename == "GroupsAboutFeedMembersCardUnit":
            member_count = unit_group.get("group_member_profiles", {}).get("formatted_count_text")

        # Created time
        elif typename == "GroupsAboutFeedActivityCardUnit":
            creation_time = unit_group.get("created_time")

    return ParserGroup(
        id=group_id,
        creation_time=creation_time,
        member_count=member_count,
        description=description,
        privacy_info=privacy_info,
        discoverability_info=discoverability_info,
    )


def parse_facebook_group_timeline(data) -> ParserTimelinePage:
    """Parse a group timeline feed into a ParserTimelinePage."""
    return _parse_timeline_feed(data, "group_feed")


def parse_timeline_app_collection_page_items(data) -> ParserCollectionPage:
    """
    Parse any TimelineAppCollection (followers, following, friends, etc.)
    """
    node = data.get("data", {}).get("node", {})
    page_items = node.get("pageItems", {})
    edges = page_items.get("edges", [])
    raw_page_info = page_items.get("page_info", {})

    items: List[ParserCollectionItem] = []
    for edge in edges:
        item_node = edge.get("node", {})
        inner_node = item_node.get("node", {})

        if inner_node.get("__typename", None) == "User":
            items.append(
                ParserProfileRef(
                    id=inner_node.get("id"),
                    name=item_node.get("title", {}).get("text"),
                    url=item_node.get("url"),
                    profile_picture_url=item_node.get("image_v2", {}).get("uri"),
                    is_verified=inner_node.get("is_verified", False),
                )
            )

        elif inner_node.get("__typename", None) == "Photo":
            photo = ParserPhotoMedia(
                id=inner_node.get("id"),
                image_url=item_node.get("image_v2", {}).get("uri"),
            )
            items.append(
                ParserMediaPost(
                    id=inner_node.get("id"),
                    url=inner_node.get("url"),
                    media=photo,
                )
            )

    return ParserCollectionPage(
        collection_id=node.get("id"),
        items=items,
        page_info=ParserPageInfo(
            has_next_page=raw_page_info.get("has_next_page", False),
            end_cursor=raw_page_info.get("end_cursor"),
        ),
    )


def parse_timeline_app_collection_aggregated_fb_shorts(data) -> ParserCollectionPage:
    """Parse a reels (aggregated_fb_shorts) collection into a ParserCollectionPage."""

    node = data.get("data", {}).get("node", {})
    aggregated_fb_shorts = node.get("aggregated_fb_shorts", {})
    edges = aggregated_fb_shorts.get("edges", [])
    raw_page_info = aggregated_fb_shorts.get("page_info", {})

    items: List[ParserCollectionItem] = []
    for edge in edges:
        item_node = edge.get("profile_reel_node", {})
        inner_node = item_node.get("node", {})

        if inner_node.get("__typename", "") != "Story":
            continue

        for attachment in inner_node.get("attachments") or []:
            media = attachment.get("media", {})

            # Facebook sometimes return null to media
            if media is None:
                continue

            if media.get("__typename") != "Video":
                continue

            video_url = None
            for item in (
                media.get("videoDeliveryResponseFragment", {})
                .get("videoDeliveryResponseResult", {})
                .get("progressive_urls", [])
            ):
                if item.get("failure_reason") is None:
                    video_url = item.get("progressive_url", None)

            actors = inner_node.get("actors") or [{}]
            a = actors[0]
            owner = media.get("owner") or {}

            reel = ParserMediaPost(
                id=media.get("id", ""),
                url=media.get("permalink_url"),
                creation_time=inner_node.get("creation_time"),
                text=(inner_node.get("message") or {}).get("text"),
                author=ParserProfileRef(
                    id=owner.get("id"),
                    name=owner.get("name"),
                    url=owner.get("url"),
                    is_verified=owner.get("is_verified"),
                    profile_picture_url=(owner.get("displayPicture") or {}).get("uri"),
                ),
                media=ParserVideoMedia(
                    id=media.get("id"),
                    length_in_second=media.get("length_in_second"),
                    creation_time=media.get("created_time"),
                    thumbnail_image_url=(media.get("thumbnailImage") or {}).get("uri"),
                    video_url=video_url,
                    play_count=media.get("play_count_reduced"),
                ),
            )

            items.append(reel)

    return ParserCollectionPage(
        collection_id=node.get("id"),
        items=items,
        page_info=ParserPageInfo(
            has_next_page=raw_page_info.get("has_next_page", False),
            end_cursor=raw_page_info.get("end_cursor"),
        ),
    )

def parse_group_members(data) -> ParserGroupMembersPage:
    """Parse a group members pagination payload into a ParserGroupMembersPage."""

    data_node = data.get("data", {}).get("node", {}) or data.get("data", {}).get("group", {})
    new_members = data_node.get("new_members", {})
    edges = new_members.get("edges", [])
    raw_page_info = new_members.get("page_info", {})

    parsed_members: List[ParserGroupMember] = []
    for edge in edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue

        membership = node.get("group_membership") or {}
        score_obj = membership.get("group_contribution_score_text")
        contribution_score = score_obj.get("text") if isinstance(score_obj, dict) else None

        parsed_members.append(
            ParserGroupMember(
                join_status=(edge.get("join_status_text") or {}).get("text"),
                contribution_score=contribution_score,
                account=ParserProfileRef(
                    id=node.get("id"),
                    name=node.get("name"),
                    url=node.get("url"),
                    profile_picture_url=(node.get("profile_picture") or {}).get("uri"),
                ),
            )
        )

    return ParserGroupMembersPage(
        members=parsed_members,
        page_info=ParserPageInfo(
            type_cursor="group_members",
            end_cursor=raw_page_info.get("end_cursor"),
            has_next_page=raw_page_info.get("has_next_page", False),
        ),
    )


def parse_facebook_serp_search(response) -> ParserSearchResults:
    """
    Parse a Facebook SERP (search engine results page) response.
    Handles user results (role == "ENTITY_USER") and post results (role == "TOP_PUBLIC_POSTS").
    """
    serp = response.get("data", {}).get("serpResponse") or response.get("serpResponse")
    if not serp:
        return ParserSearchResults()

    results = serp.get("results", {})
    edges = results.get("edges", [])

    profiles = []
    posts = []
    groups = []

    for edge in edges:
        node = edge.get("node", {})
        role = node.get("role")
        vm = edge.get("rendering_strategy", {}).get("view_model", {})
        rendering = edge.get("rendering_strategy", {})

        # --- User result ---
        if role == "ENTITY_USER":
            profile = vm.get("profile")
            if not profile or profile.get("__typename") != "User":
                continue

            profiles.append(
                ParserProfileRef(
                    id=profile.get("id"),
                    name=profile.get("name"),
                    url=profile.get("url"),
                    profile_picture_url=(profile.get("profile_picture") or {}).get("uri"),
                    is_verified=profile.get("is_verified"),
                )
            )

        # --- Post result ---
        elif role in ("TOP_PUBLIC_POSTS", "SEMANTIC_PUBLIC_POSTS", "PUBLIC_POSTS", "POSTS_WITH_RELAXATION", "FEED_POSTS", "POST_SILVER_TORCH"):
            story = vm.get("click_model", {}).get("story")
            if not story:
                continue

            feed_posts = _parse_feed_post({"node": story})
            posts.extend(feed_posts)

        # --- Group list card (VLIST module, many groups per edge) ---
        elif role == "EXPLORE_GROUPS_VLIST":
            for result in rendering.get("result_rendering_strategies", []):
                group = _extract_group_from_view_model(result.get("view_model", {}))
                if group:
                    groups.append(group)

        # --- Flat single group result (one group per edge) ---
        elif role == "ENTITY_GROUPS":
            group = _extract_group_from_view_model(rendering.get("view_model", {}))
            if group:
                groups.append(group)
        # else:
        #     print(role)

    page_info = results.get("page_info", {})
    return ParserSearchResults(
        profiles=profiles,
        posts=posts,
        groups=groups,
        page_info=ParserPageInfo(
            has_next_page=page_info.get("has_next_page", False),
            end_cursor=page_info.get("end_cursor"),
        ),
    )


def _parse_marketplace_listing(canonical_listing) -> Optional[ParserMarketplaceListing]:
    """
    Normalize a single marketplace listing (canonical_listing) into a dict.
    """
    if not canonical_listing:
        return None

    price = canonical_listing.get("listing_price") or {}
    strikethrough = canonical_listing.get("strikethrough_price") or {}
    location = canonical_listing.get("location") or {}
    reverse_geocode = location.get("reverse_geocode") or {}
    city_page = reverse_geocode.get("city_page") or {}

    seller = canonical_listing.get("marketplace_listing_seller") or {}

    photo = canonical_listing.get("primary_listing_photo") or {}
    photo_image = photo.get("image") or {}

    video = canonical_listing.get("listing_video")

    return ParserMarketplaceListing(
        id=canonical_listing.get("id"),
        title=canonical_listing.get("marketplace_listing_title"),
        category_id=canonical_listing.get("marketplace_listing_category_id"),
        currency=iso4217parse.parse(price.get("formatted_amount"))[0].alpha3
        if price.get("formatted_amount")
        else None,
        price=int(Price.fromstring(price.get("formatted_amount")).amount)
        if price.get("formatted_amount")
        else None,
        strikethrough_price=strikethrough.get("amount"),
        location=ParserMarketplaceLocation(
            city=reverse_geocode.get("city"),
            state=reverse_geocode.get("state"),
            city_page=ParserMarketplaceCityPage(
                id=city_page.get("id"),
                display_name=city_page.get("display_name"),
            ) if city_page else None,
        ) if location else None,
        is_hidden=canonical_listing.get("is_hidden"),
        is_live=canonical_listing.get("is_live"),
        is_pending=canonical_listing.get("is_pending"),
        is_sold=canonical_listing.get("is_sold"),
        min_listing_price=canonical_listing.get("min_listing_price"),
        max_listing_price=canonical_listing.get("max_listing_price"),
        created_with_seller_app=canonical_listing.get("created_with_seller_app"),
        delivery_types=canonical_listing.get("delivery_types"),
        listing_photo=ParserPhotoMedia(
            id=photo.get("id"),
            image_url=photo_image.get("uri"),
        ) if photo else None,
        video=ParserVideoMedia(id=video.get("id")) if video else None,
        seller=ParserSeller(
            profile=ParserProfileRef(
                id=seller.get("id"),
                name=seller.get("name"),
            )
        ),
    )

def parse_marketplace_search(data) -> ParserMarketplaceSearchPage:
    """Parse a marketplace search response into a ParserMarketplaceSearchPage."""

    candidates = [
        data.get("data", {}).get("marketplace_search", {}),
        data.get("marketplace_search", {}),
    ]

    all_edges = []
    raw_page_info = {}

    for entity in candidates:
        if not entity:
            continue
        feed_units = entity.get("feed_units", {}) or {}
        edges = feed_units.get("edges", [])
        if edges:
            all_edges.extend(edges)
        info = feed_units.get("page_info", {})
        if info and not raw_page_info:
            raw_page_info = info

    listings: List[ParserMarketplaceListing] = []
    for edge in all_edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue
        if node.get("__typename") != "MarketplaceFeedListingStoryObject":
            continue
        parsed = _parse_marketplace_listing(node.get("listing"))
        if parsed is not None:
            listings.append(parsed)

    return ParserMarketplaceSearchPage(
        listings=listings,
        page_info=ParserPageInfo(
            type_cursor="marketplace_search",
            end_cursor=raw_page_info.get("end_cursor"),
            has_next_page=raw_page_info.get("has_next_page", False),
        ),
    )


def _parse_marketplace_pdp_listing(target) -> Optional[ParserMarketplaceListing]:
    """
    Normalize a Marketplace PDP listing (GroupCommerceProductItem).

    `target` = data.viewer.marketplace_product_details_page.target
    """

    if not target:
        return None

    price = target.get("listing_price") or {}
    strikethrough = target.get("strikethrough_price") or {}

    story = target.get("story") or {}
    seller = target.get("marketplace_listing_seller") or {}

    description = target.get("redacted_description") or {}
    location_text = target.get("location_text") or {}

    attribute_data = target.get("attribute_data") or []

    # Price handling: prefer `amount` (already decimal), fall back to offset/100
    price_amount = None
    if price.get("amount") is not None:
        try:
            price_amount = int(float(price["amount"]))
        except (TypeError, ValueError):
            price_amount = None
    elif price.get("amount_with_offset_in_currency") is not None:
        try:
            price_amount = int(price["amount_with_offset_in_currency"]) / 100
        except (TypeError, ValueError):
            price_amount = None

    stats = seller.get("marketplace_ratings_stats_by_role_v2", {})
    seller_stats = stats.get("seller_stats", {})
    combined = stats.get("seller_buyer_combined", {})

    return ParserMarketplaceListing(
        id=target.get("id"),
        category_id=target.get("marketplace_listing_category_id"),
        url=story.get("url"),
        post_id=story.get("post_id"),
        creation_time=target.get("creation_time"),
        currency=price.get("currency"),
        price=price_amount,
        strikethrough_price=int(
            Price.fromstring(strikethrough.get("formattedAmountWithoutDecimals")).amount
        ) if strikethrough.get("formattedAmountWithoutDecimals") else None,
        location_text=location_text.get("text"),
        latitude=(target.get("location") or {}).get("latitude"),
        longitude=(target.get("location") or {}).get("longitude"),
        title=target.get("marketplace_listing_title"),
        description=description.get("text"),
        discounts_text=target.get("discounts_text"),
        is_live=target.get("is_live"),
        is_pending=target.get("is_pending"),
        is_sold=target.get("is_sold"),
        is_hidden=target.get("is_hidden"),
        is_on_marketplace=target.get("is_on_marketplace"),
        seller=ParserSeller(
            profile=ParserProfileRef(
                id=seller.get("id"),
                name=seller.get("name"),
                profile_picture_url=(seller.get("profile_picture") or {}).get("uri"),
            ),
            joined_time=seller.get("join_time"),
            verified_badge=seller.get("marketplace_should_display_verified_badge"),
            seller_ratings_are_private=stats.get("seller_ratings_are_private"),
            seller_stats=ParserSellerStats(
                five_star_ratings_average=seller_stats.get("five_star_ratings_average"),
                five_star_total_rating_count_by_role=seller_stats.get("five_star_total_rating_count_by_role"),
            ),
            seller_buyer_combined_ratings_are_private=combined.get("ratings_are_private"),
            seller_buyer_combined=ParserSellerStats(
                five_star_ratings_average=combined.get("five_star_ratings_average"),
                five_star_total_rating_count_by_role=combined.get("five_star_total_rating_count_by_role"),
            ),
        ),
        attributes=[
            ParserAttribute(name=a.get("attribute_name"), value=a.get("value"))
            for a in attribute_data
        ],
        delivery_types=target.get("delivery_types"),
        is_shipping_offered=target.get("is_shipping_offered"),
        is_buy_now_enabled=target.get("is_buy_now_enabled"),
        is_checkout_enabled=target.get("is_checkout_enabled"),
        is_cart_enabled=target.get("is_cart_enabled"),
        is_purchase_protected=target.get("is_purchase_protected"),
        inventory_count=target.get("inventory_count"),
        messaging_enabled=target.get("messaging_enabled"),
        created_with_seller_app=target.get("created_with_seller_app"),
    )


def _parse_marketplace_partner_pdp_listing(target) -> Optional[ParserMarketplaceListing]:
    """
    Normalize a partner Marketplace PDP listing (e.g. eBay).

    `target` = data.viewer.marketplace_product_details_page.target
    """
    if not target:
        return None

    price = target.get("listing_price") or {}
    story = target.get("story") or {}
    description = target.get("redacted_description") or {}
    partner_seller = (target.get("partner_seller_info") or {}).get("seller_info") or {}
    shipping = target.get("shipping_cost_info") or {}

    return ParserMarketplaceListing(
        id=target.get("id"),
        category_id=target.get("marketplace_listing_category_id"),
        url=story.get("url"),
        post_id=story.get("post_id"),
        currency=iso4217parse.parse(price.get("formatted_amount_zeros_stripped"))[0].alpha3
        if price.get("formatted_amount_zeros_stripped")
        else None,
        price=int(Price.fromstring(price.get("formatted_amount_zeros_stripped")).amount)
        if price.get("formatted_amount_zeros_stripped")
        else None,
        location_text=target.get("partner_listing_location"),
        title=target.get("marketplace_listing_title"),
        description=description.get("text"),
        is_shipping_offered=target.get("is_shipped_listing"),
        attributes=[
            ParserAttribute(name=a.get("display_name"), value=a.get("value"))
            for a in (target.get("partner_item_attribute_data") or [])
        ],
        partner=ParserPartnerSeller(
            profile=ParserProfileRef(
                id=partner_seller.get("id"),
                name=partner_seller.get("partner_seller_name"),
                profile_picture_url=partner_seller.get("seller_photo_url"),
            ),
            partner_brand_name=target.get("partner_brand_name"),
            seller_review_count=partner_seller.get("seller_review_count"),
            seller_positive_ratings_pct=partner_seller.get("seller_positive_ratings_pct"),
            seller_member_since=partner_seller.get("seller_member_since"),
            number_of_sold_listings=partner_seller.get("number_of_sold_listings"),
            average_ship_time=partner_seller.get("average_ship_time"),
        ),
        shipping_cost_text=shipping.get("shipping_cost_text"),
        has_shipping_cost=shipping.get("has_shipping_cost"),
        delivery_window_text=target.get("delivery_window_text"),
        product_details_page_uri=target.get("product_details_page_uri"),
    )

def parse_marketplace_pdp(data) -> Optional[ParserMarketplacePDP]:
    """Parse a marketplace PDP response into a ParserMarketplacePDP."""

    candidates = [
        data.get("data", {}).get("viewer", {}).get("marketplace_product_details_page", {}),
        data.get("viewer", {}).get("marketplace_product_details_page", {}),
    ]

    pdp_node = next((c for c in candidates if c), None)
    if not pdp_node:
        return None

    target = pdp_node.get("target")
    if pdp_node.get("product_details_type") == "PARTNER_LISTING":
        parsed = _parse_marketplace_partner_pdp_listing(target)
    else:
        parsed = _parse_marketplace_pdp_listing(target)
    if parsed is None:
        return None

    parsed.product_details_type = pdp_node.get("product_details_type")
    return ParserMarketplacePDP(listing=parsed)

def parse_marketplace_pdp_media(data) -> Optional[ParserMarketplaceMedia]:
    """Parse a marketplace PDP media response into a ParserMarketplaceMedia."""

    candidates = [
        data.get("data", {}).get("viewer", {}).get("marketplace_product_details_page", {}),
        data.get("viewer", {}).get("marketplace_product_details_page", {}),
    ]

    pdp_node = next((c for c in candidates if c), None)
    if not pdp_node:
        return None

    target = pdp_node.get("target")
    if not target:
        return None

    photos = [
        ParserPhotoMedia(id=p.get("id"), image_url=(p.get("image") or {}).get("uri"))
        for p in (target.get("listing_photos") or [])
        if p
    ]

    videos = [
        ParserVideoMedia(
            id=v.get("id"),
            thumbnail_image_url=(v.get("image") or {}).get("uri"),
            video_url=v.get("playable_url_hd") or v.get("playable_url"),
        )
        for v in (target.get("pre_recorded_videos") or [])
        if v
    ]

    return ParserMarketplaceMedia(
        listing_id=target.get("id"),
        is_hidden=target.get("is_hidden"),
        photos=photos,
        videos=videos,
    )

# ---------- photo / video media viewer -> ParserMediaPost ----------

def parse_media_post_photo(data) -> Optional[ParserMediaPost]:
    """Parse a photo media-viewer payload (`data.currMedia`) into a ParserMediaPost."""

    data_currMedia = data.get("data", {}).get("currMedia")
    currMedia = data.get("currMedia")
    if not data_currMedia:
        return None

    # ---- Author (owner) ----
    owner = data_currMedia.get("owner") or {}
    author_id = owner.get("id")

    # ---- Image ----
    image = data_currMedia.get("image") or {}

    # ---- Feedback (reactions + shares) ----
    data_currMedia_feedback = data_currMedia.get("feedback") or {}
    currMedia_feedback = currMedia.get("feedback") or {}

    reaction_display_strategy = None
    comments_count = None
    share_count = None
    ufi = currMedia_feedback.get("comet_ufi_summary_and_actions_renderer") or {}
    for action in (ufi.get("feedback") or {}).get(
        "adaptive_ufi_action_renderers", []
    ):
        if action.get("__typename") == "UFIStoryReactActionRenderer":
            reaction_display_strategy = (
                action.get("feedback", {}).get("reaction_display_config", {}).get("reaction_display_strategy")
            )
        if action.get("__typename") == "XFBUFIAdaptiveShareActionRenderer":
            share_count = (
                action.get("feedback", {}).get("share_count", {}).get("count")
            )

    comments_count = (
        (currMedia_feedback.get("comment_list_renderer") or {})
        .get("feedback", {})
        .get("comment_rendering_instance", {})
        .get("comments", {})
        .get("total_count")
    )

    creation_story = data_currMedia.get("creation_story") or {}
    container_story = data_currMedia.get("container_story") or {}
    text = (creation_story.get("message") or {}).get("text")

    group_id = None
    target_group = creation_story.get("target_group")
    if target_group is not None:
        group_id=target_group.get("id")
    return ParserMediaPost(
        id=data_currMedia.get("id"),
        url=currMedia.get("url"),
        creation_time=data_currMedia.get("created_time"),
        text=text,
        author=ParserProfileRef(
            id=owner.get("id"),
            name=(currMedia.get("owner") or {}).get("name"),
            profile_picture_url=((currMedia.get("owner") or {}).get("profile_picture") or {}).get("uri"),
        ),
        reactors_visible=(reaction_display_strategy == "NONE") if reaction_display_strategy else None,
        reaction_count=(data_currMedia_feedback.get("reactors") or {}).get("count"),
        comments_count=comments_count,
        share_count=share_count,
        media=ParserPhotoMedia(
            id=data_currMedia.get("id"),
            image_url=image.get("uri"),
            creation_time=data_currMedia.get("created_time"),
        ),
        nextMediaAfterNodeId=((data.get("mediaset") or {}).get("nextMediaAfterNodeId") or {}).get("id"),
        parent_post_id=container_story.get("post_id"),
        group_id=group_id,
        feedback_id=data_currMedia_feedback.get("id"),
    )

def parse_media_post_video(data) -> Optional[ParserMediaPost]:
    """Parse a Video media viewer payload into a ParserMediaPost."""
    data_currMedia = data.get("data", {}).get("currMedia")
    currMedia = data.get("currMedia") or {}
    if not data_currMedia:
        return None

    data_currMedia_creation_story = data_currMedia.get("creation_story") or {}
    data_currMedia_container_story = data_currMedia.get("container_story") or {}

    currMedia_creation_story = currMedia.get("creation_story") or {}
    currMedia_container_story = currMedia.get("creation_story") or {}

    actors = data_currMedia_creation_story.get("actors") or [{}]
    a = actors[0]

    thumbnail = (data_currMedia.get("preferred_thumbnail") or {}).get("image") or {}

    video_url = None
    for item in (
        data_currMedia
        .get("videoDeliveryResponseFragment", {})
        .get("videoDeliveryResponseResult", {})
        .get("progressive_urls", [])
    ):
        # loop and get the last one, the best one
        if item.get("failure_reason") is None:
            video_url = item.get("progressive_url", None)

    data_currMedia_feedback = data_currMedia.get("feedback") or {}
    currMedia_feedback = currMedia.get("feedback") or {}
    
    reaction_count = None
    share_count = None
    ufi = (currMedia_feedback.get("comet_ufi_summary_and_actions_renderer") or {}).get("feedback", {})
    for action in ufi.get("adaptive_ufi_action_renderers", []):
        if action.get("__typename") == "UFIStoryReactActionRenderer":
            reaction_count = action.get("feedback", {}).get("reaction_count", {}).get("count")
        elif action.get("__typename") == "XFBUFIAdaptiveShareActionRenderer":
            share_count = action.get("feedback", {}).get("share_count", {}).get("count")

    comments_count = (
        (currMedia_feedback.get("comment_list_renderer") or {})
        .get("feedback", {})
        .get("comment_rendering_instance", {})
        .get("comments", {})
        .get("total_count")
    )

    duration_ms = data_currMedia.get("playable_duration_in_ms")
    length_in_second = round(duration_ms / 1000, 1) if duration_ms else None

    video_creation_time = None
    for m in (currMedia_creation_story.get("comet_sections") or {}).get("metadata", []):
        if m.get("__typename") == "CometFeedStoryLongerTimestampStrategy":
            video_creation_time = (m.get("story") or {}).get("creation_time")
            break

    post_creation_time = None
    for m in (currMedia_container_story.get("comet_sections") or {}).get("metadata", []):
        if m.get("__typename") == "CometFeedStoryLongerTimestampStrategy":
            post_creation_time = (m.get("story") or {}).get("creation_time")
            break

    group_id = None
    target_group = data_currMedia_creation_story.get("target_group")
    if target_group is not None:
        group_id=target_group.get("id")

    return ParserMediaPost(
        id=data_currMedia.get("id"),
        url=currMedia.get("url"),
        creation_time=post_creation_time,
        text=(data_currMedia_creation_story.get("message") or {}).get("text"),
        author=ParserProfileRef(
            id=a.get("id"),
            name=a.get("name"),
            url=a.get("url"),
            is_verified=a.get("is_verified"),
        ),
        reaction_count=reaction_count,
        share_count=share_count,
        comments_count=comments_count,
        media=ParserVideoMedia(
            id=data_currMedia.get("id"),
            thumbnail_image_url=thumbnail.get("uri"),
            video_url=video_url,
            length_in_second=length_in_second,
            creation_time=video_creation_time
        ),
        nextMediaAfterNodeId=((data.get("mediaset") or {}).get("nextMediaAfterNodeId") or {}).get("id"),
        group_id=group_id,
        parent_post_id=data_currMedia_creation_story.get("post_id"),
        feedback_id=data_currMedia_feedback.get("id"),
    )

def parse_group_mediaset(data) -> Optional[ParserMediaPostsPage]:
    node = data.get("data", {}).get("node", {})

    mediaset = node.get("group_mediaset") or {}
    media = mediaset.get("media") or {}
    edges = media.get("edges", [])
    raw_page_info = media.get("page_info", {})

    group_id = node.get("id")

    media_posts: List[ParserMediaPost] = []
    for edge in edges:
        media_node = (edge or {}).get("node") or {}
        typename = media_node.get("__typename")
        media_id = media_node.get("id")
        owner = media_node.get("owner") or {}
        image = media_node.get("image") or {}
        story = media_node.get("creation_story") or {}

        if typename == "Photo":
            parsed_media = ParserPhotoMedia(
                id=media_id,
                image_url=image.get("uri"),
            )
        elif typename == "Video":
            parsed_media = ParserVideoMedia(
                id=media_id,
                thumbnail_image_url=image.get("uri"),
            )
        else:
            continue

        media_posts.append(
            ParserMediaPost(
                id=media_id,
                url=media_node.get("url"),
                text=(story.get("message") or {}).get("text"),
                group_id=group_id,
                author=ParserProfileRef(id=owner.get("id")),
                media=parsed_media,
            )
        )

    return ParserMediaPostsPage(
        media_posts=media_posts,
        page_info=ParserPageInfo(
            has_next_page=raw_page_info.get("has_next_page", False),
            end_cursor=raw_page_info.get("end_cursor"),
        ),
    )

def parse_facebook_payload(json_input) -> Optional[ParsedResponse]:
    """Dispatch a Facebook GraphQL response to its matching parser by schema fingerprint."""

    if isinstance(json_input, str):
        data = json.loads(json_input)
    else:
        data = json_input

    data_block = data.get("data", {})
    node_block = data_block.get("node", {})

    # User Collection Ids
    if "profile_header_renderer" in data_block.get("user", {}):
        return ParsedResponse(
            operation="ProfileCometHeaderQuery",
            parsed_data=parse_profile_collection_ids(data),
        )

    # User About Subtabs Info
    if "about_app_sections" in data_block.get("user", {}):
        return ParsedResponse(
            operation="ProfileCometAboutAppSectionQuery",
            parsed_data=parse_about_collections(data),
        )

    # Get User Posts (Paginable)
    if (
        node_block.get("__typename") == "User"
        and "timeline_list_feed_units" in node_block
    ):
        return ParsedResponse(
            operation="ProfileCometTimelineFeedRefetchQuery",
            parsed_data=parse_facebook_timeline(data),
        )

    # Get Single Full Post
    if "node_v2" in data_block:
        if data_block.get("node_v2") is None:
            return None 
        
        return ParsedResponse(
            operation="CometSinglePostDialogContentQuery",
            parsed_data=parse_post(data),
        )

    # Get Post Comments (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "comment_rendering_instance_for_feed_location" in node_block
    ):
        return ParsedResponse(
            operation="CommentsListComponentsPaginationQuery",
            parsed_data=parse_facebook_comments(data),
        )

    # Get Comment Replies (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "replies_connection" in node_block
    ):
        edges = node_block.get("replies_connection").get("edges")
        if edges and "is_subreply_parent_deleted" in edges[0].get("node"):
            return ParsedResponse(
                operation="Depth1CommentsListPaginationQuery",
                parsed_data=parse_comment_replies(data, comment_type="reply"),
            )
        else:
            return ParsedResponse(
                operation="Depth2CommentsListPaginationQuery",
                parsed_data=parse_comment_replies(data, comment_type="subreply"),
            )

    # Get Post/Comments Reactors (Full Detailed Reactors) (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "reactors" in node_block
        and "top_reactions" not in node_block
    ):
        return ParsedResponse(
            operation="CometUFIReactionsDialogTabContentRefetchQuery",
            parsed_data=parse_reactors(data),
        )

    # Group Hovercard Fingerprint
    if (
        "comet_hovercard_renderer" in node_block
        and node_block.get("__typename") == "Group"
    ):
        return ParsedResponse(
            operation="CometHovercardQueryRendererQuery",
            parsed_data=parse_facebook_group_hovercard(data),
        )

    # Group Initial Page / Metadata Payload
    if "about_feed_units" in data_block.get("group", {}):
        return ParsedResponse(
            operation="CometGroupAboutRootQuery",
            parsed_data=parse_group_about_info(data),
        )

    # Group Timeline Feed
    if node_block.get("__typename") == "Group" and "group_feed" in node_block:
        return ParsedResponse(
            operation="GroupsCometFeedRegularStoriesPaginationQuery",
            parsed_data=parse_facebook_group_timeline(data),
        )

    # Group Member List (Paginable)
    if node_block.get("__typename") == "Group" and "new_members" in node_block:
        return ParsedResponse(
            operation="GroupsCometMembersPageNewMembersSectionRefetchQuery",
            parsed_data=parse_group_members(data),
        )

    # TimelineAppCollection Collection: Followers, Followees, Friends, Reels, Photos
    if (
        node_block.get("__typename") == "TimelineAppCollection"
        and "pageItems" in node_block
    ):
        return ParsedResponse(
            operation="ProfileCometAppCollectionListRendererPaginationQuery",
            parsed_data=parse_timeline_app_collection_page_items(data),
        )

    # TimelineAppCollection Collection: Reels (More details for Reels)
    if (
        node_block.get("__typename") == "TimelineAppCollection"
        and "aggregated_fb_shorts" in node_block
    ):
        return ParsedResponse(
            operation="ProfileCometAppCollectionReelsRendererPaginationQuery",
            parsed_data=parse_timeline_app_collection_aggregated_fb_shorts(data),
        )

    if "marketplace_product_details_page" in (data_block.get("viewer", {}) or {}):
        pdp = data_block["viewer"]["marketplace_product_details_page"]
        target = (pdp or {}).get("target") or {}

        if "listing_photos" in target or "pre_recorded_videos" in target:
            return ParsedResponse(
                operation="MarketplacePDPC2CMediaViewerWithImagesQuery",
                parsed_data=parse_marketplace_pdp_media(data),
            )
        else:
            return ParsedResponse(
                operation="MarketplacePDPContainerQuery",
                parsed_data=parse_marketplace_pdp(data),
            )

    if "serpResponse" in data_block:
        return ParsedResponse(
            operation="SearchCometResultsPaginatedResultsQuery",
            parsed_data=parse_facebook_serp_search(data),
        )

    # Marketplace Search (Paginable)
    if "marketplace_search" in data_block:
        return ParsedResponse(
            operation="CometMarketplaceSearchContentPaginationQuery",
            parsed_data=parse_marketplace_search(data),
        )

    # Photo MediaPost
    if (data_block.get("currMedia") or {}).get("__typename") == "Photo":
        return ParsedResponse(
            operation="CometPhotoRootContentQuery",
            parsed_data=parse_media_post_photo(data),
        )

    # Video MediaPost
    if (data_block.get("currMedia") or {}).get("__typename") == "Video":
        return ParsedResponse(
            operation="CometPhotoRootContentQuery",
            parsed_data=parse_media_post_video(data),
        )

    # Group media set (paginated photo gallery/ paginated video gallery)
    if node_block.get("__typename") == "Group" and "group_mediaset" in node_block:
        return ParsedResponse(
            operation="GroupsCometMediaPhotosTabGridQuery/GroupsCometMediaVideosTabGridQuery",
            parsed_data=parse_group_mediaset(data),
        )

    # Unrecognized Schema
    return None

def json_default(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True)
    return str(obj)

if __name__ == "__main__":
    with open("facebook2.json", "r", encoding="utf-8") as f:
        parsed_dict = parse_facebook_payload(f.read())
        with open("facebook4.json", "w", encoding="utf-8") as f:
            json.dump(parsed_dict, f, indent=2, ensure_ascii=False, default=json_default)
