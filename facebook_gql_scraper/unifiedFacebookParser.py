import json
import base64

import iso4217parse
from price_parser import Price

# Fixed schema keys grouped by tab name
FIXED_TABS_SCHEMA = {
    "About": [
        "directory_basic_info",
        "directory_specialties",
        "directory_intro",
        "directory_category",
        "directory_personal_details",
        "directory_links",
        "directory_communities",
        "directory_offers",
        "directory_work",
        "directory_education",
        "directory_activites",
        "directory_interests",
        "directory_travel",
        "directory_contact_info",
        "directory_privacy_and_legal_info",
        "directory_names",
    ],
    "Followers": [
        "followers",
        "followers_mutual",
        "following",
        "following_mutual",
        "friends_all",
        "friends_mutual",
    ],
    "Friends": [
        "friends_all",
        "friends_mutual",
        "friends_recent",
        "friends_with_upcoming_birthdays",
        "friends_work",
        "friends_college",
        "friends_high_school",
        "friends_current_city",
        "friends_hometown",
        "followers",
        "following",
        "followers_mutual",
        "following_mutual",
    ],
    "Photos": [
        "photos_by",
        "photos_albums",
        "photos_of",
    ],
    "Reels": ["owner_reels"],
}


def _parse_comment_attachments(attachments):
    """
    Parse the `attachments` list on a comment / reply.
    Returns a list of normalized attachment dicts (photo / video / sticker / genericMedia).
    """
    result = []
    for attachment in attachments:
        inner_attachment = attachment.get("style_type_renderer", {}).get(
            "attachment", {}
        )
        attachment_type = inner_attachment.get("media", {}).get("__typename", "")

        if attachment_type == "Photo":
            result.append(
                {
                    "type": "photo",
                    "id": inner_attachment.get("media", {}).get("id", None),
                    "image_url": (
                        inner_attachment.get("media", {})
                        .get("image", {})
                        .get("uri", None)
                    ),
                    "url": inner_attachment.get("url", None),
                }
            )

        elif attachment_type == "Video":
            result.append(
                {
                    "type": "video",
                    "id": inner_attachment.get("media", {}).get("id", None),
                    "fallback_image_url": (
                        inner_attachment.get("media", {})
                        .get("fallback_image", {})
                        .get("uri", None)
                    ),
                    "url": inner_attachment.get("url", None),
                }
            )

        elif attachment_type == "Sticker":
            sticker = {
                "type": "sticker",
                "id": inner_attachment.get("media", {}).get("id", None),
                "label": inner_attachment.get("media", {}).get("label", None),
                "image_url": (
                    inner_attachment.get("media", {}).get("image", {}).get("uri", None)
                ),
            }
            pack = inner_attachment.get("media", {}).get("pack", None)
            if pack is not None:
                sticker["pack"] = {
                    "id": pack.get("id", None),
                    "name": pack.get("name", None),
                }
            result.append(sticker)

        elif attachment_type == "GenericAttachmentMedia":
            # Most likely a GIF
            if (
                attachment.get("style_type_renderer", {}).get("__typename", "")
                == "StoryAttachmentAnimatedImageShareStyleRenderer"
            ):
                result.append(
                    {
                        "type": "genericMedia",
                        "id": inner_attachment.get("media", {}).get("id", None),
                        "image_url": (
                            inner_attachment.get("media", {})
                            .get("image", {})
                            .get("uri", None)
                        ),
                        "genericMedia_url": (
                            inner_attachment.get("media").get("animated_image") or {}
                        ).get("uri", None),
                        "animated_image_attribution": inner_attachment.get(
                            "media", {}
                        ).get("animated_image_attribution", None),
                    }
                )

        # else:
        #     print(f"Uncaught Attachment Type: {attachment_type}")

    return result


def _parse_post_attachments(attachments):
    """
    Parse the `attachments` list on a post (album or single item).
    Returns a list of normalized attachment dicts (photo / video / genericMedia).
    """
    result = []
    for att in attachments:
        # Check if album, or Single Item
        if "__typename" not in att.get("styles", {}):
            continue
        style_type = att.get("styles", {}).get("__typename", "")

        if style_type == "StoryAttachmentAlbumStyleRenderer":
            for subattachment_node in (
                att.get("styles", {})
                .get("attachment", {})
                .get("all_subattachments", {})
                .get("nodes", [])
            ):
                subattachment_type = subattachment_node.get("media", {}).get(
                    "__typename", ""
                )

                if subattachment_type == "Video":
                    video_url = None
                    for item in (
                        subattachment_node.get("media", {})
                        .get("video_grid_renderer", {})
                        .get("video", {})
                        .get("videoDeliveryResponseFragment", {})
                        .get("videoDeliveryResponseResult", {})
                        .get("progressive_urls", [])
                    ):
                        # loop and get the last one, the best one
                        if item.get("failure_reason") is None:
                            video_url = item.get("progressive_url", None)

                    result.append(
                        {
                            "type": "video",
                            "id": subattachment_node.get("media", {}).get("id", None),
                            "thumbnail_image_url": (
                                subattachment_node.get("media", {})
                                .get("video_grid_renderer", {})
                                .get("video", {})
                                .get("preferred_thumbnail", {})
                                .get("image", {})
                                .get("uri", None)
                            ),
                            "video_url": video_url,
                            "url": subattachment_node.get("url", None),
                        }
                    )
                elif subattachment_type == "Photo":
                    result.append(
                        {
                            "type": "photo",
                            "id": subattachment_node.get("media", {}).get("id", None),
                            "image_url": (
                                subattachment_node.get("media", {})
                                .get("image", {})
                                .get("uri", None)
                            ),
                            "url": subattachment_node.get("url", None),
                        }
                    )
                # else:
                #     print(f"Uncaught SubAttachment Type: {subattachment_type}")

        else:
            style_type = (
                att.get("styles", {})
                .get("attachment", {})
                .get("media", {})
                .get("__typename", "")
            )
            if style_type == "Photo":
                result.append(
                    {
                        "type": "photo",
                        "id": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("id", None)
                        ),
                        "image_url": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("photo_image", {})
                            .get("uri", None)
                        ),
                        "url": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("url", None)
                        ),
                    }
                )

            elif style_type == "Video":
                video_url = None
                for item in (
                    att.get("styles", {})
                    .get("attachment", {})
                    .get("media", {})
                    .get("videoDeliveryResponseFragment", {})
                    .get("videoDeliveryResponseResult", {})
                    .get("progressive_urls", [])
                ):
                    # loop and get the last one, the best one
                    if item.get("failure_reason") is None:
                        video_url = item.get("progressive_url", None)

                result.append(
                    {
                        "type": "video",
                        "id": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("id", None)
                        ),
                        "length_in_second": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("length_in_second", None)
                        ),
                        "thumbnail_image_url": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("preferred_thumbnail", {})
                            .get("image", {})
                            .get("uri", None)
                        ),
                        "video_url": video_url,
                        "url": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("permalink_url", None)
                        ),
                    }
                )

            elif style_type == "GenericAttachmentMedia":
                result.append(
                    {
                        "type": "genericMedia",
                        "id": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("id", None)
                        ),
                        "image_url": (
                            att.get("styles", {})
                            .get("attachment", {})
                            .get("media", {})
                            .get("image", {})
                            .get("uri", None)
                        ),
                        "genericMedia_url": (
                            att.get("styles", {}).get("attachment", {}).get("url", None)
                        ),
                    }
                )

            # else:
            #     print(f"Uncaught Attachment Type: {style_type}")

    return result


def _parse_reactions_from_ufi(target):
    """
    Parse reactions + share_count from a feedback target.

    `target` is the `feedback_target_with_context` dict.
    Returns (reactions_dict, share_count).
    """
    reactions = {"total": 0, "breakdown": []}
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
        count = edge.get("reaction_count", 0)
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
        .get("total_count", 0)
    )


def _parse_feed_post(edge):
    """Build a normalized post dict from a feed edge (user timeline or group feed)."""
    node = edge.get("node", {})

    post_id = node.get("post_id")
    if not post_id:
        return None

    ufi_container = (
        node.get("comet_sections", {})
        .get("feedback", {})
        .get("story", {})
        .get("story_ufi_container", {})
        .get("story", {})
    )
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

    attachments_list = _parse_post_attachments(node.get("attachments", []))

    comet_story = node.get("comet_sections", {}).get("content", {}).get("story", {})
    text = None
    if comet_story.get("message", None) is not None:
        text = comet_story.get("message", {}).get("text", None)

    return {
        "type": "post",
        "id": node.get("post_id", None),
        "creation_time": node.get("creation_time", None),
        "url": (
            node.get("comet_sections", {})
            .get("content", {})
            .get("story", {})
            .get("wwwURL", None)
        ),
        "author": {
            "type": "profile",
            "id": node.get("actors", [{}])[0].get("id", None),
            "name": node.get("actors", [{}])[0].get("name", None),
            "url": node.get("actors", [{}])[0].get("url", None),
        },
        "title": title_text,
        "text": text,
        "attachments": attachments_list,
        "reactions": reactions,
        "reactors_visible": reaction_display_strategy == "NONE"
        if reaction_display_strategy
        else None,
        "share_count": share_count,
        "comments_count": comments_count,
    }


def _parse_timeline_feed(data, feed_key):
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

    posts = []
    for edge in all_edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue
        parsed = _parse_feed_post(edge)
        if parsed is not None:
            posts.append(parsed)
    return {
        "posts": posts,
        "page_info": {
            "type_cursor": "posts",
            "end_cursor": raw_page_info.get("end_cursor"),
            "has_next_page": raw_page_info.get("has_next_page", False),
        },
    }


def _extract_group_from_view_model(vm):
    """Build a normalized group dict from a SearchProfileViewModel."""
    profile = vm.get("profile")
    if not profile or profile.get("__typename") != "Group":
        return None

    return {
        "type": "group",
        "id": profile.get("id"),
        "name": profile.get("name"),
        "url": profile.get("url") or profile.get("profile_url"),
        "profile_picture_url": profile.get("profile_picture", {}).get("uri"),
    }


def parse_profile_collection_ids(data: dict) -> dict:
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

    for content in user.get("profile_social_context").get("content", []):
        text = content.get("text", {}).get("text")
        if text.endswith("friends"):
            friends_count = text.removesuffix("friends").strip()
        if text.endswith("followers"):
            followers_count = text.removesuffix("followers").strip()
        if text.endswith("following"):
            followees_count = text.removesuffix("following").strip()

    author_profile = {
        "id": user.get("id", None),
        "name": user.get("name", None),
        "alternate_name": user.get("alternate_name", None),
        "gender": user.get("gender", None),
        "url": user.get("url", None),
        "status_text": status_text,
        "profile_picture_url": user.get("profilePicLarge", {}).get("uri", None),
        "is_verified": user.get("show_verified_badge_on_profile", None),
        "followers_count": followers_count,
        "followees_count": followees_count,
        "friends_count": friends_count,
    }

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
            # Extract Tab/Section ID
            parsed_tabs[tab_name]["id"] = node.get("id")

            # Extract Collection IDs
            collections = node.get("all_collections", {}).get("nodes", [])
            for col in collections:
                col_key = col.get("tab_key")
                col_id = col.get("id")
                if col_key in parsed_tabs[tab_name]["collections"]:
                    parsed_tabs[tab_name]["collections"][col_key] = col_id
        #         else:
        #             print(f"Uncaughted [{tab_name}] col_key: {col_key}")
        # else:
        #     print(f"Uncaughted Tab: {tab_name}")
    return {"author_profile": author_profile, "tabs": parsed_tabs}


def parse_about_collections(data: dict) -> dict:
    """
    Extracts text contents specifically for 'About' tab section keys.
    """
    # Initialize schema keys with default None values
    about_data = {}

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
                result = {"category": None, "items": []}
                sec_type = field_sec.get("field_section_type")
                result["category"] = field_sec.get("title", {}).get("text", None)
                # Match against defined About section keys
                # if sec_type in about_data:
                profile_fields_nodes = field_sec.get("profile_fields", {}).get(
                    "nodes", []
                )
                for node in profile_fields_nodes:
                    result_item = {"title": None, "text": None, "item": []}

                    # 1. Primary title text extraction
                    title_text = (
                        node.get("title", {}).get("text") if node.get("title") else None
                    )
                    result_item["title"] = title_text
                    for item in node.get("list_item_groups", []):
                        for subitem in item.get("list_items", []):
                            result_item["item"].append(
                                subitem.get("text").get("text", None)
                            )

                    if node.get("renderer") is not None:
                        text_content = (
                            node.get("renderer", {})
                            .get("field", {})
                            .get("text_content", None)
                        )

                        if text_content is not None:
                            result_item["text"] = text_content.get("text", None)

                        text_content2 = node.get("renderer", {}).get(
                            "text_content", None
                        )
                        if text_content2 is not None:
                            result_item["text"] = text_content2.get("text", None)

                        for travel_item in node.get("renderer", {}).get(
                            "travel_profile_items", []
                        ):
                            travel_name = travel_item.get("page").get("name")
                            visit_time = travel_item.get("visit_time")
                            result_item["item"].append(f"{travel_name}:{visit_time}")

                        # for renderer_item in node.get("renderer", {}).get("field", {}).get("list_item_groups", []):
                        #     if renderer_item.get("has_items") == True:
                        #         for subrenderer_item in renderer_item.get("list_items", []):
                        #             result_item["item"].append(subrenderer_item.get("text").get("text"))

                    result["items"].append(result_item)

                about_data[sec_type] = result

    return {"About": about_data}


def parse_post(data):

    # Navigate node_v2 directly via dictionary access
    node_v2 = data.get("data", {}).get("node_v2", {})
    comet_story = node_v2.get("comet_sections", {}).get("content", {}).get("story", {})
    comet_story_layout = (
        node_v2.get("comet_sections", {}).get("context_layout", {}).get("story", {})
    )

    # Extract Comments
    comments_list = []
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

    for edge in comment_data.get("edges", []):
        c_node = edge.get("node", {})

        decoded = base64.b64decode(c_node.get("id")).decode("utf-8")
        post_id, comment_id = decoded.split(":")[-1].split("_", 1)

        text = None
        body = c_node.get("body", None)
        if body:
            text = body.get("text", None)

        attachments = _parse_comment_attachments(c_node.get("attachments", []))

        comments_list.append(
            {
                "type": "comment",
                "id": comment_id,
                "text": text,
                "attachments": attachments,
                "created_time": c_node.get("created_time", None),
                "reaction_count": (
                    c_node.get("feedback", {}).get("reactors", {}).get("count_reduced")
                ),
                "reply_count": (
                    c_node.get("feedback", {})
                    .get("replies_fields", {})
                    .get("total_count", None)
                ),
                "reply_expansion_token": (
                    c_node.get("feedback", {})
                    .get("expansion_info", {})
                    .get("expansion_token", None)
                ),
                "author": {
                    "type": "profile",
                    "id": c_node.get("author", {}).get("id", None),
                    "name": c_node.get("author", {}).get("name", None),
                    "gender": c_node.get("author", {}).get("gender", None),
                    "url": c_node.get("author", {}).get("url", None),
                    "profile_picture_url": (
                        c_node.get("author", {})
                        .get("profile_picture_depth_0", {})
                        .get("uri", None)
                    ),
                },
                "post_id": post_id,
            }
        )

    reactions, reaction_display_strategy, share_count = _parse_reactions_from_ufi(
        target
    )

    attachments_list = _parse_post_attachments(node_v2.get("attachments", []))

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
    # Consolidated extracted data dict
    parsed_post = {
        "type": "post",
        "id": node_v2.get("post_id", None),
        "creation_time": node_v2.get("creation_time", None),
        "url": comet_story.get("wwwURL", None),
        "author": {
            "type": "profile",
            "id": comet_story.get("actors", [{}])[0].get("id", None),
            "name": comet_story.get("actors", [{}])[0].get("name", None),
            "url": comet_story.get("actors", [{}])[0].get("url", None),
            "profile_picture_url": (
                comet_story.get("actors", [{}])[0]
                .get("profile_picture", {})
                .get("uri", None)
            ),
        },
        "title": title_text,
        "text": text,
        "attachments": attachments_list,
        "reactions": reactions,
        "reactors_visible": reaction_display_strategy == "NONE"
        if reaction_display_strategy
        else None,
        "share_count": share_count,
        "comments_count": comment_data.get("total_count", None),
        "comments": comments_list,
    }

    return {
        "post": parsed_post,
        "page_info": {
            "type_cursor": "comments",
            "end_cursor": comment_data.get("page_info", {}).get("end_cursor"),
            "has_next_page": comment_data.get("page_info", {}).get(
                "has_next_page", False
            ),
            "has_previous_page": comment_data.get("page_info", {}).get(
                "has_previous_page", False
            ),
            "start_cursor": comment_data.get("page_info", {}).get("start_cursor"),
        },
    }


def parse_post_reactors_partial(data):

    feedback = data.get("data", {}).get("feedback", {})

    # Extract Base64 feedback ID and decode post ID
    raw_id = feedback.get("id", "")
    post_id = None
    if raw_id:
        decoded = base64.b64decode(raw_id).decode("utf-8")
        post_id = decoded.split(":")[-1]


    # Parse individual reactor list
    reactors_data = feedback.get("reactors", {})
    reactors_list = [
        {"id": node.get("id"), "name": node.get("name")}
        for node in reactors_data.get("nodes", [])
    ]

    return {
        "post_id": post_id,
        "feedback_id": raw_id,
        "total_reactions": feedback.get("total_reaction_count", {}).get("count", 0),
        "sample_reactors_count": reactors_data.get("count", 0),
        "reactors": reactors_list,
    }


def parse_reactors(data):

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
            {
                "reaction_type_id": edge.get("feedback_reaction_info", {}).get(
                    "id", None
                ),
                "author": {
                    "type": "profile",
                    "id": user_node.get("id", None),
                    "name": user_node.get("name", None),
                    "url": user_node.get("profile_url", None),
                    "profile_picture_url": user_node.get("profile_picture", {}).get(
                        "uri", None
                    ),
                },
            }
        )

    result = {
        "post_id": post_id,
        "reactors": reactors,
        "page_info": {
            "type_cursor": "reactors",
            "has_next_page": raw_page_info.get("has_next_page", False),
            "end_cursor": raw_page_info.get("end_cursor"),
        },
    }

    # Add comment_id only if it exists
    if comment_id:
        result["parent_comment"] = {"comment_id": comment_id}

    return result


def parse_facebook_comments(data):
    """
    Parses a Facebook GraphQL response and returns a list of cleaned comment objects.
    Accepts either a JSON string or a dictionary.
    """

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
            {
                "type": "comment",
                "id": comment_id,
                "text": text,
                "attachments": attachments,
                "created_time": node.get("created_time", None),
                "reaction_count": (
                    node.get("feedback", {})
                    .get("reactors", {})
                    .get("count_reduced", None)
                ),
                "reply_count": (node.get("feedback", {}).get("replies_fields", {})).get(
                    "total_count", None
                ),
                "reply_expansion_token": (
                    node.get("feedback", {})
                    .get("expansion_info", {})
                    .get("expansion_token", None)
                ),
                "author": {
                    "type": "profile",
                    "id": author.get("id", None),
                    "name": author.get("name", None),
                    "gender": author.get("gender", None),
                    "url": author.get("url", None),
                    "profile_picture_url": author.get(
                        "profile_picture_depth_0", {}
                    ).get("uri", None),
                },
                "post_id": post_id,
            }
        )

    return {
        "comments": parsed_comments,
        "page_info": {
            "type_cursor": "comments",
            "end_cursor": comments_data.get("page_info", {}).get("end_cursor", None),
            "has_next_page": comments_data.get("page_info", {}).get(
                "has_next_page", None
            ),
            "has_previous_page": comments_data.get("page_info", {}).get(
                "has_previous_page", None
            ),
            "start_cursor": comments_data.get("page_info", {}).get(
                "start_cursor", None
            ),
        },
    }


def parse_comment_replies(data, comment_type="reply"):
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

        attachments = _parse_comment_attachments(reply_node.get("attachments", []))

        comment = {
            "type": "comment",
            "id": comment_id,
            "text": text,
            "attachments": attachments,
            "created_time": reply_node.get("created_time", None),
            "reaction_count": (
                reply_node.get("feedback", {})
                .get("reactors", {})
                .get("count_reduced", None)
            ),
            "author": {
                "type": "profile",
                "id": reply_node.get("author", {}).get("id", None),
                "name": reply_node.get("author", {}).get("name", None),
                "gender": reply_node.get("author", {}).get("gender", None),
                "url": reply_node.get("author", {}).get("url", None),
                "profile_picture_url": (
                    reply_node.get("author", {})
                    .get("profile_picture_depth_0", {})
                    .get("uri", None)
                ),
            },
            "parent_comment": {
                "comment_id": parent_comment_id,
                "author": {
                    "type": "profile",
                    "name": comment_direct_parent.get("author", {}).get("name", None),
                    "gender": comment_direct_parent.get("author", {}).get(
                        "gender", None
                    ),
                },
            },
            "post_id": post_id,
        }

        if comment_type == "reply":
            comment["reply_count"] = (
                reply_node.get("feedback", {})
                .get("replies_fields", {})
                .get("total_count", None)
            )
            comment["reply_expansion_token"] = (
                reply_node.get("feedback", {})
                .get("expansion_info", {})
                .get("expansion_token", None)
            )

        parsed_replies.append(comment)

    return {
        "replies": parsed_replies,
        "page_info": {
            "type_cursor": "comment_replies",
            "end_cursor": replies_conn.get("page_info", {}).get("end_cursor"),
            "has_next_page": replies_conn.get("page_info", {}).get(
                "has_next_page", False
            ),
            "has_previous_page": replies_conn.get("page_info", {}).get(
                "has_previous_page", False
            ),
            "start_cursor": replies_conn.get("page_info", {}).get("start_cursor"),
        },
    }


def parse_comment_reactors_partial(data):

    feedback = data.get("data", {}).get("feedback", {})
    raw_id = feedback.get("id")

    feedback_id = base64.b64decode(raw_id).decode("utf-8")[-1]

    # Split decoded feedback ID into post_id and comment_id if both exist
    post_id, comment_id = None, None
    if feedback_id and "_" in feedback_id:
        post_id, comment_id = feedback_id.split("_", 1)
    else:
        post_id = feedback_id

    summary_list = feedback.get("top_reactions", {}).get("summary", [])
    reactions_summary = []

    for item in summary_list:
        reactors = [
            {
                "id": reactor.get("id"),
                "name": reactor.get("name"),
                "typename": reactor.get("__typename"),
            }
            for reactor in item.get("interesting_reactors", [])
        ]

        reactions_summary.append(
            {
                "reaction_id": item.get("reaction", {}).get("id"),
                "count": item.get("reaction_count"),
                "count_reduced": item.get("reaction_count_reduced"),
                "reactors": reactors,
            }
        )

    return {
        "feedback_id": feedback_id,
        "post_id": post_id,
        "comment_id": comment_id,
        "reactions_summary": reactions_summary,
    }


def parse_facebook_user_hovercard(data):

    # Navigate to user data in comet_hovercard_renderer
    node = data.get("data", {}).get("node", {})
    user = node.get("comet_hovercard_renderer", {}).get("user", {})

    # Extract raw timeline context strings (Bio, Category, Links, Followers)
    context_nodes = user.get("timeline_context_items", {}).get("nodes", [])
    context_details = [
        item.get("title", {}).get("text")
        for item in context_nodes
        if item.get("title", {}).get("text")
    ]

    # Map contextual items dynamically
    category = next(
        (
            item
            for item in context_details
            if "Page ·" in item or "creator" in item.lower()
        ),
        None,
    )
    followers = next(
        (item for item in context_details if "followers" in item.lower()), None
    )

    return {
        "type": "profile",
        "id": user.get("id") or node.get("id"),
        "name": user.get("name"),
        "url": user.get("profile_url") or user.get("url"),
        "is_verified": user.get("is_verified", False),
        "is_memorialized": user.get("is_visibly_memorialized", False),
        "profile_picture": user.get("profile_picture", {}).get("uri"),
        "category": category,
        "followers": followers,
        "timeline_context": context_details,
    }


def parse_facebook_group_hovercard(data):

    node = data.get("data", {}).get("node", {})
    group = node.get("comet_hovercard_renderer", {}).get("group", {})

    # Extract sample members from the facepile list
    facepile_edges = group.get("facepile_profiles", {}).get("edges", [])
    sample_members = [
        {
            "type": "profile",
            "id": edge.get("node", {}).get("id"),
            "name": edge.get("node", {}).get("name"),
            "url": edge.get("node", {}).get("url"),
            "profile_picture_url": (
                edge.get("node", {}).get("profile_picture", {}).get("uri")
            ),
        }
        for edge in facepile_edges
        if edge.get("node")
    ]

    return {
        "type": "group",
        "id": group.get("id") or node.get("id"),
        "name": group.get("name"),
        "url": group.get("profile_url") or group.get("url"),
        "privacy": group.get("privacy_info", {}).get("title", {}).get("text"),
        "member_count": group.get("group_member_profiles", {}).get(
            "formatted_count_text"
        ),
        "profile_picture_url": group.get("profile_picture", {}).get("uri"),
        "sample_members": sample_members,
    }


def parse_user_summary(data):
    """
    Parses user.
    """
    # Target the exact user node path
    user = data.get("data", {}).get("user", {})
    delegate_page = user.get("delegate_page", None)

    account = {
        "account": {
            "type": "profile",
            "id": user.get("id"),
        }
    }

    if delegate_page is not None:
        account["account"]["name"] = delegate_page.get("name")
        account["account"]["category"] = delegate_page.get("category_name")
        account["account"]["description"] = delegate_page.get("best_description").get(
            "text", None
        )
        account["account"]["bio"] = delegate_page.get("best_description", {}).get(
            "text"
        )
        account["account"]["profile_picture_url"] = delegate_page.get(
            "profile_picture_uri"
        )

    return account


def parse_facebook_timeline(data):
    return _parse_timeline_feed(data, "timeline_list_feed_units")


def parse_group_about_info(data) -> dict:
    group_data = data.get("data", {}).get("group", {})
    feed_units = group_data.get("about_feed_units", [])

    result = {
        "type": "group",
        "id": group_data.get("id"),
        "created_time": None,
        "member_count": None,
        "description": None,
        "privacy_info": None,
        "discoverability_info": None,
    }

    for unit in feed_units:
        typename = unit.get("__typename")
        unit_group = unit.get("group", {})

        # Fallback to unit-level ID if not present at the top level
        if not result["id"] and unit_group.get("id"):
            result["id"] = unit_group.get("id")

        # Description, Privacy, and Discoverability
        if typename == "GroupsAboutFeedAboutCardUnit":
            desc_entities = unit_group.get("description_with_entities", {})
            result["description"] = desc_entities.get("text")

            for item in unit_group.get("about_info_items", []):
                item_type = item.get("__typename")
                item_group = item.get("group", {})

                if item_type == "XFBPrivacyGroupsAboutInfoItem":
                    result["privacy_info"] = (
                        item_group.get("privacy_info").get("label").get("text")
                    )
                elif item_type == "XFBDiscoverabilityGroupsAboutInfoItem":
                    result["discoverability_info"] = (
                        item_group.get("discoverability_info").get("label").get("text")
                    )

        # Member count via formatted_count_text
        elif typename == "GroupsAboutFeedMembersCardUnit":
            result["member_count"] = unit_group.get("group_member_profiles", {}).get(
                "formatted_count_text"
            )

        # Created time
        elif typename == "GroupsAboutFeedActivityCardUnit":
            result["created_time"] = unit_group.get("created_time")

    return result


def parse_facebook_group_timeline(data):
    return _parse_timeline_feed(data, "group_feed")


def parse_timeline_app_collection_page_items(data):
    """
    Parse any TimelineAppCollection (followers, following, friends, etc.)
    """

    node = data.get("data", {}).get("node", {})
    page_items = node.get("pageItems", {})
    edges = page_items.get("edges", [])
    raw_page_info = page_items.get("page_info", {})

    result = {
        "collection_id": node.get("id"),
    }
    items = []
    for edge in edges:
        item_node = edge.get("node", {})
        inner_node = item_node.get("node", {})
        if inner_node.get("__typename", None) == "User":
            items.append(
                {
                    "type": "profile",
                    "id": inner_node.get("id"),
                    "name": item_node.get("title", {}).get("text"),
                    "url": item_node.get("url"),
                    "profile_picture_url": item_node.get("image_v2", {}).get("uri"),
                    "is_verified": inner_node.get("is_verified", False),
                }
            )

        elif inner_node.get("__typename", None) == "Photo":
            items.append(
                {
                    "type": "photo",
                    "id": inner_node.get("id", None),
                    "image_url": item_node.get("image_v2").get("uri", None),
                    "url": inner_node.get("url"),
                }
            )

    result["items"] = items
    result["page_info"] = {
        "has_next_page": raw_page_info.get("has_next_page", False),
        "end_cursor": raw_page_info.get("end_cursor"),
    }
    return result


def parse_timeline_app_collection_aggregated_fb_shorts(data):
    """
    Parse any TimelineAppCollection BUT Specifically for Reels
    """

    node = data.get("data", {}).get("node", {})
    aggregated_fb_shorts = node.get("aggregated_fb_shorts", {})
    edges = aggregated_fb_shorts.get("edges", [])
    raw_page_info = aggregated_fb_shorts.get("page_info", {})

    result = {
        "collection_id": node.get("id"),
    }
    items = []
    for edge in edges:
        item_node = edge.get("profile_reel_node", {})
        inner_node = item_node.get("node", {})

        if inner_node.get("__typename", "") == "Story":
            for attachment in inner_node.get("attachments", None):
                if attachment.get("media", {}).get("__typename", "") == "Video":
                    video_url = None
                    for item in (
                        attachment.get("media", {})
                        .get("videoDeliveryResponseFragment", {})
                        .get("videoDeliveryResponseResult", {})
                        .get("progressive_urls", [])
                    ):
                        # loop and get the last one, the best one
                        if item.get("failure_reason") is None:
                            video_url = item.get("progressive_url", None)

                    items.append(
                        {
                            "type": "video",
                            "id": attachment.get("media", {}).get("id", None),
                            "length_in_second": attachment.get("media", {}).get(
                                "length_in_second", None
                            ),
                            "created_time": attachment.get("media", {}).get(
                                "created_time", None
                            ),
                            "thumbnail_image_url": (
                                attachment.get("media", {})
                                .get("thumbnailImage", {})
                                .get("uri", None)
                            ),
                            "video_url": video_url,
                            "url": attachment.get("media", {}).get(
                                "permalink_url", None
                            ),
                            "post": {
                                "type": "post",
                                "id": inner_node.get("post_id", None),
                                "creation_time": inner_node.get("creation_time", None),
                                "text": (inner_node.get("message") or {}).get(
                                    "text", None
                                ),
                                "author": {
                                    "type": "profile",
                                    "id": inner_node.get("actors", [{}])[0].get(
                                        "id", None
                                    ),
                                    "name": inner_node.get("actors", [{}])[0].get(
                                        "name", None
                                    ),
                                    "url": inner_node.get("actors", [{}])[0].get(
                                        "url", None
                                    ),
                                    "is_verified": inner_node.get("actors", [{}])[
                                        0
                                    ].get("is_verified", None),
                                },
                            },
                            "author": {
                                "type": "profile",
                                "id": (
                                    attachment.get("media", {})
                                    .get("owner", {})
                                    .get("id", None)
                                ),
                                "name": (
                                    attachment.get("media", {})
                                    .get("owner", {})
                                    .get("name", None)
                                ),
                                "url": (
                                    attachment.get("media", {})
                                    .get("owner", {})
                                    .get("url", None)
                                ),
                                "is_verified": (
                                    attachment.get("media", {})
                                    .get("owner", {})
                                    .get("is_verified", None)
                                ),
                                "profile_picture_url": (
                                    attachment.get("media", {})
                                    .get("owner", {})
                                    .get("displayPicture", {})
                                    .get("uri", None)
                                ),
                            },
                            "play_count": attachment.get("media", {}).get(
                                "play_count_reduced", None
                            ),
                        }
                    )

    result["items"] = items
    result["page_info"] = {
        "has_next_page": raw_page_info.get("has_next_page", False),
        "end_cursor": raw_page_info.get("end_cursor"),
    }
    return result


def parse_group_member_summary(data):
    """Parses FB Group JSON for group ID, member counts, admins, and members.

    Ignores the 'Things in Common' section and extracts page_info pagination data.
    """
    group = data.get("data", {}).get("group", {})

    def extract_account(node: dict) -> dict:
        if not node:
            return {}
        return {
            "type": "profile",
            "id": node.get("id"),
            "name": node.get("name"),
            "url": node.get("url"),
            "profile_picture_url": node.get("profile_picture", {}).get("uri"),
            "category": node.get("profile_plus_category_display_name"),
            "bio": node.get("bio_text", {}).get("text")
            if isinstance(node.get("bio_text"), dict)
            else None,
            "follower_count": node.get("follower_count", None),
        }

    # 2. Extract Admins
    admin_data = group.get("group_admin_profiles", {})
    admin_edges = admin_data.get("edges", [])

    admins_list = [
        {"account": extract_account(edge.get("node"))}
        for edge in admin_edges
        if edge.get("node")
    ]

    # 3. Extract Members (Excluding GroupThingsInCommonSection)
    members_list = []

    # Iterate through paginated sections and skip 'GroupThingsInCommonSection'
    new_members = group.get("new_members", {})
    for edge in new_members.get("edges", []):
        node = edge.get("node")

        points = None
        if (
            node.get("group_membership", {}).get("group_contribution_score_text", None)
            is not None
        ):
            points = (
                node.get("group_membership", {})
                .get("group_contribution_score_text", {})
                .get("text", None)
            )

        members_list.append(
            {
                "join_status": edge.get("join_status_text", {}).get("text", None),
                "points": points,
                "account": extract_account(node),
            }
        )

    return {
        "id": group.get("id", None),
        "member_count": group.get("group_member_profiles", {}).get("count", None),
        "admin_count": admin_data.get("count", len(admins_list)),
        "admins": {
            "accounts": admins_list,
            "page_info": {
                "type_cursor": "members",
                "has_next_page": admin_data.get("page_info", {}).get(
                    "has_next_page", None
                ),
                "end_cursor": admin_data.get("page_info", {}).get("end_cursor", None),
            },
        },
        "members": {
            "accounts": members_list,
            "page_info": {
                "type_cursor": "members",
                "has_next_page": new_members.get("page_info", {}).get(
                    "has_next_page", None
                ),
                "end_cursor": new_members.get("page_info", {}).get("end_cursor", None),
            },
        },
    }


def parse_group_members(data):
    """
    Parses Facebook group members from a GraphQL payload using the
    standardized account and pagination schema used across the parser module.
    """

    # Navigate to new_members node safely across different response wrappers
    data_node = data.get("data", {}).get("node", {}) or data.get("data", {}).get(
        "group", {}
    )
    new_members = data_node.get("new_members", {})

    edges = new_members.get("edges", [])
    raw_page_info = new_members.get("page_info", {})

    parsed_members = []
    for edge in edges:
        if not edge:
            continue

        node = edge.get("node", {})
        if not node:
            continue

        # Extract contribution score if present
        membership = node.get("group_membership") or {}
        score_obj = membership.get("group_contribution_score_text")
        contribution_score = (
            score_obj.get("text") if isinstance(score_obj, dict) else None
        )

        # Extract bio safely
        bio_obj = node.get("bio_text")
        bio = bio_obj.get("text") if isinstance(bio_obj, dict) else None

        parsed_members.append(
            {
                "join_status": edge.get("join_status_text", {}).get("text", None),
                "contribution_score": contribution_score,
                "account": {
                    "type": "profile",
                    "id": node.get("id", None),
                    "name": node.get("name", None),
                    "url": node.get("url", None),
                    "profile_picture_url": node.get("profile_picture", {}).get(
                        "uri", None
                    ),
                    "category": node.get("profile_plus_category_display_name", None),
                    "bio": bio,
                    "follower_count": node.get("follower_count", None),
                },
            }
        )

    return {
        "members": parsed_members,
        "page_info": {
            "type_cursor": "group_members",
            "end_cursor": raw_page_info.get("end_cursor", None),
            "has_next_page": raw_page_info.get("has_next_page", False),
            "has_previous_page": raw_page_info.get("has_previous_page", False),
            "start_cursor": raw_page_info.get("start_cursor", None),
        },
    }


def parse_facebook_serp_search(response):
    """
    Parse a Facebook SERP (search engine results page) response.
    Handles user results (role == "ENTITY_USER") and post results (role == "TOP_PUBLIC_POSTS").
    """
    serp = response.get("data", {}).get("serpResponse") or response.get("serpResponse")
    if not serp:
        return {"profiles": [], "posts": [], "page_info": {}}

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
                {
                    "type": "profile",
                    "id": profile.get("id", None),
                    "name": profile.get("name", None),
                    "url": profile.get("url", None),
                    "profile_picture_url": profile.get("profile_picture", {}).get(
                        "uri", None
                    ),
                    "is_verified": profile.get("is_verified", None),
                }
            )

        # --- Post result ---
        elif role in ("TOP_PUBLIC_POSTS", "SEMANTIC_PUBLIC_POSTS", "PUBLIC_POSTS"):
            story = vm.get("click_model", {}).get("story")
            if not story:
                continue

            parsed_post = _parse_feed_post({"node": story})
            if parsed_post:
                posts.append(parsed_post)

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

    page_info = results.get("page_info", {})
    return {
        "profiles": profiles,
        "posts": posts,
        "groups": groups,
        "page_info": {
            "has_next_page": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        },
    }


def _parse_marketplace_listing(canonical_listing):
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

    return {
        "type": "marketplace_listing",
        "id": canonical_listing.get("id", None),
        "title": canonical_listing.get("marketplace_listing_title", None),
        "category_id": canonical_listing.get("marketplace_listing_category_id", None),
        "currency": iso4217parse.parse(price.get("formatted_amount"))[0].alpha3
        if price.get("formatted_amount")
        else None,
        "price": int(Price.fromstring(price.get("formatted_amount")).amount)
        if price.get("formatted_amount")
        else None,
        "strikethrough_price": strikethrough.get("amount", None),
        "location": {
            "city": reverse_geocode.get("city", None),
            "state": reverse_geocode.get("state", None),
            "city_page": {
                "id": city_page.get("id", None),
                "display_name": city_page.get("display_name", None),
            }
            if city_page
            else None,
        },
        "is_hidden": canonical_listing.get("is_hidden", None),
        "is_live": canonical_listing.get("is_live", None),
        "is_pending": canonical_listing.get("is_pending", None),
        "is_sold": canonical_listing.get("is_sold", None),
        "min_listing_price": canonical_listing.get("min_listing_price", None),
        "max_listing_price": canonical_listing.get("max_listing_price", None),
        "marketplace_listing_category_id": canonical_listing.get(
            "marketplace_listing_category_id", None
        ),
        "created_with_seller_app": canonical_listing.get(
            "created_with_seller_app", None
        ),
        "delivery_types": canonical_listing.get("delivery_types", None),
        "listing_photo": {
            "type": "photo",
            "id": photo.get("id", None),
            "image_url": photo_image.get("uri", None),
        }
        if photo
        else None,
        "video": {
            "type": "video",
            "id": video.get("id", None),
        }
        if video
        else None,
        "seller": {
            "profile": {
                "type": "profile",
                "id": seller.get("id", None),
                "name": seller.get("name", None),
            }
        },
    }


def parse_user_marketplace(data):
    """
    Parse a user's marketplace_listing_sets connection.

    Handles both `data.node` and top-level `node` response shapes,
    aggregating edges from either (or both) and returning normalized
    listings plus pagination metadata.
    """
    candidates = [
        data.get("data", {}).get("node", {}),
        data.get("node", {}),
    ]

    all_edges = []
    raw_page_info = {}

    for entity in candidates:
        if not entity:
            continue

        listing_sets = entity.get("marketplace_listing_sets", {}) or {}
        edges = listing_sets.get("edges", [])
        if edges:
            all_edges.extend(edges)

        info = listing_sets.get("page_info", {})
        if info and not raw_page_info:
            raw_page_info = info

    listings = []
    for edge in all_edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue

        canonical_listing = node.get("canonical_listing")
        parsed = _parse_marketplace_listing(canonical_listing)
        if parsed is None:
            continue

        listings.append(parsed)

    return {
        "listings": listings,
        "page_info": {
            "type_cursor": "user_marketplace_listings",
            "end_cursor": raw_page_info.get("end_cursor"),
            "has_next_page": raw_page_info.get("has_next_page", False),
        },
    }


def parse_marketplace_search(data):
    """
    Parse a marketplace_search feed_units connection.

    Handles both `data.marketplace_search` and top-level
    `marketplace_search` response shapes, aggregating edges from
    either (or both) and returning normalized listings plus
    pagination metadata.

    Note: feed_units contains mixed node types (listing stories,
    SERP banners, SERP headers). Only listing stories are parsed;
    non-listing nodes are skipped.
    """
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

    listings = []
    for edge in all_edges:
        if not edge:
            continue
        node = edge.get("node", {})
        if not node:
            continue

        # Only parse listing story nodes; skip banners/headers
        if node.get("__typename") != "MarketplaceFeedListingStoryObject":
            continue

        listing = node.get("listing")
        parsed = _parse_marketplace_listing(listing)
        if parsed is None:
            continue

        listings.append(parsed)

    return {
        "listings": listings,
        "page_info": {
            "type_cursor": "marketplace_search",
            "end_cursor": raw_page_info.get("end_cursor"),
            "has_next_page": raw_page_info.get("has_next_page", False),
        },
    }


def _parse_marketplace_pdp_listing(target):
    """
    Normalize a marketplace PDP listing (GroupCommerceProductItem) into a dict.

    `target`   = data.viewer.marketplace_product_details_page.target

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

    return {
        "type": "marketplace_listing",
        "id": target.get("id"),
        "category_id": target.get("marketplace_listing_category_id"),
        "url": story.get("url"),
        "post_id": story.get("post_id"),
        "creation_time": target.get("creation_time"),
        "currency": price.get("currency"),
        "price": price_amount,
        "strikethrough_price": int(
            Price.fromstring(strikethrough.get("formattedAmountWithoutDecimals")).amount
        )
        if strikethrough.get("formattedAmountWithoutDecimals")
        else None,
        "location_text": location_text.get("text"),
        "latitude": (target.get("location") or {}).get("latitude"),
        "longitude": (target.get("location") or {}).get("longitude"),
        "title": target.get("marketplace_listing_title"),
        "description": description.get("text"),
        "discounts_text": target.get("discounts_text"),
        "is_live": target.get("is_live"),
        "is_pending": target.get("is_pending"),
        "is_sold": target.get("is_sold"),
        "is_hidden": target.get("is_hidden"),
        "is_on_marketplace": target.get("is_on_marketplace"),
        "seller": {
            "profile": {
                "type": "profile",
                "id": seller.get("id"),
                "name": seller.get("name"),
                "profile_picture_url": seller.get("profile_picture", {}).get("uri"),
                "joined_time": seller.get("join_time"),
            },
            "verified_badge": seller.get("marketplace_should_display_verified_badge"),
            "seller_ratings_are_private": (
                seller.get("marketplace_ratings_stats_by_role_v2", {}).get(
                    "seller_ratings_are_private"
                )
            ),
            "seller_stats": {
                "five_star_ratings_average": (
                    seller.get("marketplace_ratings_stats_by_role_v2", {})
                    .get("seller_stats", {})
                    .get("five_star_ratings_average")
                ),
                "five_star_total_rating_count_by_role": (
                    seller.get("marketplace_ratings_stats_by_role_v2", {})
                    .get("seller_stats", {})
                    .get("five_star_total_rating_count_by_role")
                ),
            },
            "seller_buyer_combined_ratings_are_private": (
                seller.get("marketplace_ratings_stats_by_role_v2", {})
                .get("seller_buyer_combined", {})
                .get("ratings_are_private")
            ),
            "seller_buyer_combined": {
                "five_star_ratings_average": (
                    seller.get("marketplace_ratings_stats_by_role_v2", {})
                    .get("seller_buyer_combined", {})
                    .get("five_star_ratings_average")
                ),
                "five_star_total_rating_count_by_role": (
                    seller.get("marketplace_ratings_stats_by_role_v2", {})
                    .get("seller_buyer_combined", {})
                    .get("five_star_total_rating_count_by_role")
                ),
            },
        },
        "attributes": [
            {"name": a.get("attribute_name"), "value": a.get("value")}
            for a in attribute_data
        ],
        "delivery_types": target.get("delivery_types"),
        "is_shipping_offered": target.get("is_shipping_offered"),
        "is_buy_now_enabled": target.get("is_buy_now_enabled"),
        "is_checkout_enabled": target.get("is_checkout_enabled"),
        "is_cart_enabled": target.get("is_cart_enabled"),
        "is_purchase_protected": target.get("is_purchase_protected"),
        "inventory_count": target.get("inventory_count"),
        "messaging_enabled": target.get("messaging_enabled"),
        "created_with_seller_app": target.get("created_with_seller_app"),
        # -------------------------
        # Partner fields
        # -------------------------
        "partner": {
            "profile": {
                "type": "profile",
                "id": None,
                "name": None,
                "profile_picture_url": None,
            },
            "partner_brand_name": None,
            "seller_review_count": None,
            "seller_positive_ratings_pct": None,
            "seller_member_since": None,
            "number_of_sold_listings": None,
            "average_ship_time": None,
        },
        "shipping_cost_text": None,
        "has_shipping_cost": None,
        "delivery_window_text": None,
        "product_details_page_uri": None,
    }


def _parse_marketplace_partner_pdp_listing(target):
    """
    Normalize a partner marketplace PDP listing (ProductItem, e.g. eBay)
    into a dict.

    `target` = data.viewer.marketplace_product_details_page.target
    """
    if not target:
        return None

    price = target.get("listing_price") or {}
    story = target.get("story") or {}
    description = target.get("redacted_description") or {}
    partner_seller = (target.get("partner_seller_info") or {}).get("seller_info") or {}
    shipping = target.get("shipping_cost_info") or {}

    return {
        "type": "marketplace_listing",
        "id": target.get("id"),
        "category_id": target.get("marketplace_listing_category_id"),
        "url": story.get("url"),
        "post_id": story.get("post_id"),
        "creation_time": None,
        "currency": iso4217parse.parse(price.get("formatted_amount_zeros_stripped"))[
            0
        ].alpha3
        if price.get("formatted_amount_zeros_stripped")
        else None,
        "price": int(
            Price.fromstring(price.get("formatted_amount_zeros_stripped")).amount
        )
        if price.get("formatted_amount_zeros_stripped")
        else None,
        "strikethrough_price": None,
        "location_text": target.get("partner_listing_location"),
        "latitude": None,
        "longitude": None,
        "title": target.get("marketplace_listing_title"),
        "description": description.get("text"),
        "discounts_text": None,
        "is_live": None,
        "is_pending": None,
        "is_sold": None,
        "is_hidden": None,
        "is_on_marketplace": None,
        "seller": {
            "profile": {
                "type": "profile",
                "id": None,
                "name": None,
                "profile_picture_url": None,
                "joined_time": None,
            },
            "verified_badge": None,
            "seller_ratings_are_private": None,
            "seller_stats": {
                "five_star_ratings_average": None,
                "five_star_total_rating_count_by_role": None,
            },
            "seller_buyer_combined_ratings_are_private": None,
            "seller_buyer_combined": {
                "five_star_ratings_average": None,
                "five_star_total_rating_count_by_role": None,
            },
        },
        "attributes": [
            {"name": a.get("display_name"), "value": a.get("value")}
            for a in (target.get("partner_item_attribute_data") or [])
        ],
        "delivery_types": None,
        "is_shipping_offered": target.get("is_shipped_listing"),
        "is_buy_now_enabled": None,
        "is_checkout_enabled": None,
        "is_cart_enabled": None,
        "is_purchase_protected": None,
        "inventory_count": None,
        "messaging_enabled": None,
        "created_with_seller_app": None,
        # -------------------------
        # Partner fields
        # -------------------------
        "partner": {
            "profile": {
                "type": "profile",
                "id": partner_seller.get("id"),
                "name": partner_seller.get("partner_seller_name"),
                "profile_picture_url": partner_seller.get("seller_photo_url"),
            },
            "partner_brand_name": target.get("partner_brand_name"),
            "seller_review_count": partner_seller.get("seller_review_count"),
            "seller_positive_ratings_pct": partner_seller.get(
                "seller_positive_ratings_pct"
            ),
            "seller_member_since": partner_seller.get("seller_member_since"),
            "number_of_sold_listings": partner_seller.get("number_of_sold_listings"),
            "average_ship_time": partner_seller.get("average_ship_time"),
        },
        "shipping_cost_text": shipping.get("shipping_cost_text"),
        "has_shipping_cost": shipping.get("has_shipping_cost"),
        "delivery_window_text": target.get("delivery_window_text"),
        "product_details_page_uri": target.get("product_details_page_uri"),
    }


def parse_marketplace_pdp(data):
    """
    Parse a Marketplace Product Details Page (PDP) payload.

    Handles both `data.viewer.marketplace_product_details_page` and
    top-level `viewer.marketplace_product_details_page`.

    Returns a single listing (PDP is per-item, not paginated).
    """
    candidates = [
        data.get("data", {})
        .get("viewer", {})
        .get("marketplace_product_details_page", {}),
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

    parsed["product_details_type"] = pdp_node.get("product_details_type")

    return {"listing": parsed}


def parse_marketplace_pdp_media(data):
    """
    Parse the media-only marketplace PDP payload.

    Meta splits the PDP GraphQL query into two responses: one for the
    listing fields, one for the media (photos + videos). This parses
    the media response.

    Handles both `data.viewer.marketplace_product_details_page` and
    top-level `viewer.marketplace_product_details_page`.

    Returns a single media bundle (PDP is per-item, not paginated).
    """
    candidates = [
        data.get("data", {})
        .get("viewer", {})
        .get("marketplace_product_details_page", {}),
        data.get("viewer", {}).get("marketplace_product_details_page", {}),
    ]

    pdp_node = next((c for c in candidates if c), None)
    if not pdp_node:
        return None

    target = pdp_node.get("target")
    if not target:
        return None

    listing_id = target.get("id")

    photos = []
    for photo in target.get("listing_photos") or []:
        if not photo:
            continue
        image = photo.get("image") or {}
        photos.append(
            {
                "type": "photo",
                "id": photo.get("id"),
                "image_url": image.get("uri"),
            }
        )

    videos = []
    for video in target.get("pre_recorded_videos") or []:
        if not video:
            continue
        videos.append(
            {
                "type": "video",
                "id": video.get("id", None),
                "thumbnail_image_url": video.get("image").get("uri", None),
                "playable_url": video.get("playable_url", None),
                "playable_url_hd": video.get("playable_url_hd", None),
            }
        )

    media = {
        "type": "marketplace_pdp_media",
        "listing_id": listing_id,
        "is_hidden": target.get("is_hidden"),
        "photos": photos,
        "videos": videos,
    }

    return {
        "media": media,
    }


def parse_facebook_payload(json_input):
    if isinstance(json_input, str):
        data = json.loads(json_input)
    else:
        data = json_input

    data_block = data.get("data", {})
    node_block = data_block.get("node", {})

    # User Profile [Hovercard] [Less Detailed]
    # if "comet_hovercard_renderer" in node_block and node_block.get("__typename") == "User":
    #     return {
    #         "type": "user_partial",
    #         "parsed_data": parse_facebook_user_hovercard(data)
    #     }

    # User Collection Ids
    if "profile_header_renderer" in data_block.get("user", {}):
        return {
            "operation": "ProfileCometHeaderQuery",
            "parsed_data": parse_profile_collection_ids(data),
        }

    # User About Subtabs Info
    if "about_app_sections" in data_block.get("user", {}):
        return {
            "operation": "ProfileCometAboutAppSectionQuery",
            "parsed_data": parse_about_collections(data),
        }

    # User summary
    # if "timeline_list_feed_units" in (data.get('user') or data.get('data', {}).get('user') or {}):
    #     return {
    #         "type": "user_summary",
    #         "parsed_data": parse_user_summary(data)
    #     }

    # Get User Posts (Paginable)
    if (
        node_block.get("__typename") == "User"
        and "timeline_list_feed_units" in node_block
    ):
        return {
            "operation": "ProfileCometTimelineFeedRefetchQuery",
            "parsed_data": parse_facebook_timeline(data),
        }

    # Get Single Full Post
    if "node_v2" in data_block:
        return {
            "operation": "CometSinglePostDialogContentQuery",
            "parsed_data": parse_post(data),
        }

    # Get Post Reactors (Less Detailed Reactors) [Hovercard]
    # if "important_reactors" in (data_block.get("feedback") or {}):
    #     return {
    #         "type": "post_reactors_partial",
    #         "parsed_data": parse_post_reactors_partial(data)
    #     }

    # Get Post Comments (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "comment_rendering_instance_for_feed_location" in node_block
    ):
        return {
            "operation": "CommentsListComponentsPaginationQuery",
            "parsed_data": parse_facebook_comments(data),
        }

    # Get Comment Replies (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "replies_connection" in node_block
    ):
        edges = node_block.get("replies_connection").get("edges")
        if edges and "is_subreply_parent_deleted" in edges[0].get("node"):
            return {
                "operation": "Depth1CommentsListPaginationQuery",
                "parsed_data": parse_comment_replies(data, comment_type="reply"),
            }
        else:
            return {
                "operation": "Depth2CommentsListPaginationQuery",
                "parsed_data": parse_comment_replies(data, comment_type="subreply"),
            }

    # Get Comment Reactors (Less Detailed Reactors) [Hovercard]
    # if "top_reactions" in (data_block.get("feedback") or {}):
    #     return {
    #         "type": "comment_reactors_partial",
    #         "parsed_data": parse_comment_reactors_partial(data)
    #     }

    # Get Post/Comments Reactors (Full Detailed Reactors) (Paginable)
    if (
        node_block.get("__typename") == "Feedback"
        and "reactors" in node_block
        and not "top_reactions" in node_block
    ):
        return {
            "operation": "CometUFIReactionsDialogTabContentRefetchQuery",
            "parsed_data": parse_reactors(data),
        }

    # Group Hovercard Fingerprint
    if (
        "comet_hovercard_renderer" in node_block
        and node_block.get("__typename") == "Group"
    ):
        return {
            "operation": "CometHovercardQueryRendererQuery",
            "parsed_data": parse_facebook_group_hovercard(data),
        }

    # Group Initial Page / Metadata Payload
    if "about_feed_units" in data_block.get("group", {}):
        return {
            "operation": "CometGroupAboutRootQuery",
            "parsed_data": parse_group_about_info(data),
        }

    # Group Timeline Feed
    if node_block.get("__typename") == "Group" and "group_feed" in node_block:
        return {
            "operation": "GroupsCometFeedRegularStoriesPaginationQuery",
            "parsed_data": parse_facebook_group_timeline(data),
        }

    # Group Member Summary
    # if "group_member_profiles" in data_block.get("group", {}):
    #     return {
    #         "type": "group_member_summary",
    #         "parsed_data": parse_group_member_summary(data)
    #     }

    # Group Member List (Paginable)
    if node_block.get("__typename") == "Group" and "new_members" in node_block:
        return {
            "operation": "GroupsCometMembersPageNewMembersSectionRefetchQuery",
            "parsed_data": parse_group_members(data),
        }
    # TimelineAppCollection Collection: Followers, Followees, Friends, Reels, Photos
    if (
        node_block.get("__typename") == "TimelineAppCollection"
        and "pageItems" in node_block
    ):
        return {
            "operation": "ProfileCometAppCollectionListRendererPaginationQuery",
            "parsed_data": parse_timeline_app_collection_page_items(data),
        }

    # TimelineAppCollection Collection: Reels (More details for Reels)
    if (
        node_block.get("__typename") == "TimelineAppCollection"
        and "aggregated_fb_shorts" in node_block
    ):
        return {
            "operation": "ProfileCometAppCollectionReelsRendererPaginationQuery",
            "parsed_data": parse_timeline_app_collection_aggregated_fb_shorts(data),
        }

    # User Marketplace Listings (Paginable)
    # if "marketplace_listing_sets" in node_block:
    #     return {
    #         "type": "user_marketplace",
    #         "parsed_data": parse_user_marketplace(data)
    #     }

    if "marketplace_product_details_page" in (data_block.get("viewer", {}) or {}):
        pdp = data_block["viewer"]["marketplace_product_details_page"]
        target = (pdp or {}).get("target") or {}

        # Media payload: has listing_photos / pre_recorded_videos
        if "listing_photos" in target or "pre_recorded_videos" in target:
            return {
                "operation": "MarketplacePDPC2CMediaViewerWithImagesQuery",
                "parsed_data": parse_marketplace_pdp_media(data),
            }

        # Main PDP payload: has listing_price / marketplace_listing_title / story
        else:
            return {
                "operation": "MarketplacePDPContainerQuery",
                "parsed_data": parse_marketplace_pdp(data),
            }

    if "serpResponse" in data_block:
        return {
            "operation": "SearchCometResultsPaginatedResultsQuery",
            "parsed_data": parse_facebook_serp_search(data),
        }

    # Marketplace Search (Paginable)
    if "marketplace_search" in data_block:
        return {
            "operation": "CometMarketplaceSearchContentPaginationQuery",
            "parsed_data": parse_marketplace_search(data),
        }

    # Unrecognized Schema
    return None


if __name__ == "__main__":
    with open("facebook2.json", "r", encoding="utf-8") as f:
        parsed_dict = parse_facebook_payload(f.read())
        with open("facebook4.json", "w", encoding="utf-8") as f:
            json.dump(parsed_dict, f, indent=2, ensure_ascii=False)
