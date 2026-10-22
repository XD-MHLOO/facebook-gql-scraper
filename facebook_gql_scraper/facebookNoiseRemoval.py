import json

# List of keys to remove (UI/React/Relay garbage)
REMOVE_KEYS = {
    # React/Relay internals
    "__isFeedUnit", "__isICometStorySection", "__isStoryAttachmentStyleRendererUnion",
    "__isTrackableFeedUnit", "__isVideoOwner",
    "__module_operation_", "__module_component_", "__dr",

    # UI rendering (remove CSS-like structures, but NOT "text")
    # "styles",  # need to KEEP this
    "style_list", "attributes", "children", "tag", "checksum",
    "deduplication_key", "serialized_frtp_identifiers", "unconnected_waist_data",
    "trackingdata", "viewability_config", "client_view_config",
    
    # Tracking
    "tracking", "encrypted_tracking", "encrypted_click_tracking", 
    "click_tracking_linkshim_cb", "ghl_mocked_encrypted_link",
    "ghl_label", "ghl_label_mocked_cta_button",
    
    # UI containers
    # "comet_sections", # need to KEEP for "comet_sections"
    "comet_footer_renderer", "comet_ufi_reaction_icon_renderer",
    "comet_unified_video_menu_trigger", "content_type_renderer",
    "comet_comment_author_name_and_badges_renderer",
    
    # UI flags
    "future_of_feed_info", "is_prod_eligible", "cache_id", "matched_terms",
    "debug_info", "brand_safety_data", "sponsored_data", "th_dat_spo",
    "should_host_actor_link_in_watch", "easy_hide_button_story",
    "is_regulation_enforced", "local_alerts_story_menu_promotion",
    "has_commerce_attachment", "should_show_photosensitive_content_warning",
    
    # Comment UI (these are wrappers, keep removing them)
    "comment_menu_tooltip", "should_show_comment_menu", 
    "comment_action_links", "inline_survey_config", "spam_display_mode",
    "is_hidden_by_viewer", "is_disabled", "elevated_comment_data",
    "inline_replies_expander_renderer", "comment_cover",
    
    # Reaction UI
    # "reaction_display_config",  (need to KEEP for reaction visibility info)
    "supported_reaction_infos",
    "comet_ufi_reaction_icon_renderer", "animation",
    
    # Badges
    "comet_comment_author_badges", "comet_meta_gen_comment_source_renderer",
    
    # Plugins
    "plugins", "comment_moderation_filter_restriction_notice",
    "comments_disabled_notice_renderer",
    
    # Other UI (keep permalink and wwwURL)
    # "wwwURL", "seo_title", "seo_web_crawler_lookaside_url",  # keep these
    "seo_web_crawler_lookaside_url",
    # "permalink_url",  # keep this
    "whatsapp_ad_context", "schema_context",
    "renderLocation", "privacySelectorRenderLocation",
    
    # Video player UI - KEEP "videoDeliveryResponseFragment"
    "video_player_shaka_performance_logger_init",
    "video_player_shaka_performance_logger_should_sample",
    "video_player_shaka_performance_logger_init2",
    "video_player_scrubber_preview_renderer",
    "video_player_scrubber_base_content_renderer",
    "videoDeliveryLegacyFields", 
    # "videoDeliveryResponseFragment",  # Needed for Video Details
    "dash_prefetch_experimental", "video_available_captions_locales",
    "can_use_oz", "min_quality_preference", "spherical_video_fallback_urls",
    "comet_video_player_nextgendash_availability",
    "captions_url", "animated_image_caption", "pmv_metadata",
    "latency_sensitive_config", "live_playback_instrumentation_configs",
    "p2p_settings", "audio_settings", "captions_settings",
    "broadcast_low_latency_config", "muted_segments",
    "spherical_video_renderer", "video_imf_data",
    "playback_language_on_comet", "warning_screen_renderer",
    
    # DRM
    "drm_info", "widevine_cert",
    
    # Metadata
    "server_metadata", "sr_payload", "extensions", "is_final",
}


def clean_data(obj):
    """Recursively remove UI/React/Relay garbage from data"""
    
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip if key in REMOVE_KEYS or starts with "__module" or "__dr"
            if key in REMOVE_KEYS or key.startswith("__module") or key.startswith("__dr"):
                continue
            # Recursively clean value
            cleaned[key] = clean_data(value)
        return cleaned
    
    elif isinstance(obj, list):
        return [clean_data(item) for item in obj if item is not None]
    
    else:
        return obj

def remove_raw_facebook_json_noise(data: dict):
    """Clean raw Facebook JSON data."""
    return clean_data(data)


def remove_raw_facebook_json_file_noise(input_file: str, output_file: str = "facebook3.json"):
    """Read Facebook JSON, clean it, and save to output file."""
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # print("Cleaning UI/React/Relay garbage...")
    cleaned = remove_raw_facebook_json_noise(data)
    
    # print(f"Saving to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    return cleaned


if __name__ == "__main__":
    remove_raw_facebook_json_file_noise("facebook2.json", "facebook3.json")