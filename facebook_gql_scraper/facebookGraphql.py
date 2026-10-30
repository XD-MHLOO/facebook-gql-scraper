import json
import base64
import logging
import os
import re
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Literal

import requests

from . import __version__
from .facebookConsolidater import consolidate_jsonl
from .unifiedFacebookParser import parse_facebook_payload
from .exceptions import (
    DocIdStillInvalidError,
    DtsgTokenStillInvalidError,
    DtsgTokenFetchError,
    SessionExpiredError,
    SchemaChangedError,
)
from .facebookNoiseRemoval import remove_raw_facebook_json_noise
from .facebookOperationDiscovery import FacebookOperationDiscovery

logger = logging.getLogger(__name__)


class FacebookContext:
    """
    Facebook request context.

    Manages the shared session, cookies, and GraphQL request state.

    :param cookies_file: Path to the Facebook cookies JSON file.
    :param state_file: Path to the saved Facebook request state.
    :param user_agent: User-Agent used for Facebook requests.
    :param proxy: Proxy URL used for Facebook HTTP/HTTPS requests. Supports proxies with optional authentication, e.g. ``http://user:password@host:port``.
    :param quiet: Whether to suppress progress messages.
    :param debug: Whether to save debug request/response data.
    :param debug_dir: Directory for debug files.
    """

    def __init__(
        self,
        cookies_file: str = "facebook_cookies.json",
        state_file: str = "facebook_state.json",
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None,
        quiet: bool = False,
        debug: bool = False,
        debug_dir: str = "graphql_debug",
    ):
        self.quiet = quiet
        self.debug = debug
        self.debug_dir = debug_dir
        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "user-agent": user_agent,
                "accept": "*/*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "cache-control": "no-cache",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://web.facebook.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "sec-fetch-site": "same-origin",
                # Below are optional to have
                "referer": "https://web.facebook.com/",
                "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
                "sec-ch-ua-full-version-list": '"Chromium";v="152.0.7977.83", "Not?A_Brand";v="24.0.0.0", "Google Chrome";v="152.0.7977.83"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-model": '""',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-platform-version": '"19.0.0"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
            }
        )

        if proxy:
            self.session.proxies.update(
                {
                    "http": proxy,
                    "https": proxy,
                }
            )
            self.session.verify = False

        self._cookies_file = cookies_file
        self._state_file = state_file

        # --- doc-id caches ---
        self.operations = {}  # { operation_name: doc_id }
        self.page_operations = {}  # { reference_page_url: { operation_name: doc_id } }

        self.operation_discovery: FacebookOperationDiscovery= FacebookOperationDiscovery(self)


        # --- dtsg token (lazy, refreshed on demand) ---
        self.fb_dtsg = None

        self._load_cookies()
        self._load_state()

    def progress(self, message):
        """User-facing status. Visible by default. Silenced by quiet=True."""
        if not self.quiet:
            print(message, flush=True)

    def _load_cookies(self):
        """Load cookies from the cookies file into the session. No-op if file missing."""
        try:
            with open(self._cookies_file, "r", encoding="utf-8") as f:
                raw_cookies = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Facebook cookies file not found: {self._cookies_file}"
            ) from e

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in cookies file: {self._cookies_file}"
            ) from e

        cookies = {
            c["name"]: c["value"] for c in raw_cookies if "name" in c and "value" in c
        }
        self.session.cookies.update(cookies)

    def _load_state(self):
        """Attempt to load previously-saved state (operations + fb_dtsg)."""
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError):
            return

        if state.get("version") != __version__:
            logger.info(
                "Discarding cached state: saved with version %r, current is %r",
                state.get("version"),
                __version__,
            )
            return

        self.operations = state.get("operations") or {}
        self.fb_dtsg = state.get("fb_dtsg")

    def _save_state(self):
        """Persist operation doc-ids and the dtsg token to disk."""

        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": __version__,
                    "operations": self.operations,
                    # "page_operations": self.page_operations,
                    "fb_dtsg": self.fb_dtsg,
                },
                f, indent=2, ensure_ascii=False,
            )

    def _check_session_dead(self, response) -> None:
        """Return True if the session is dead, False otherwise."""
        all_headers = response.headers
        set_cookie = all_headers.get("set-cookie", "") or ""
        set_login = all_headers.get("set-login", "") or ""

        if ("c_user=deleted" in set_cookie) or ("logged-out" in set_login):
            return True
        return False

    def _classify_error(self, response) -> Optional[str]:
        """Return 'schema', 'doc_id', or None from a GraphQL error response."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None

        messages = [
            (err or {}).get("message", "") for err in (data.get("errors") or [])
        ]

        for msg in messages:
            if "missing_required_variable_value" in msg:
                return "schema"
        for msg in messages:
            if "GraphQL document with ID" in msg and "was not found" in msg:
                return "doc_id"
        return None

    # ------------------------------------------------------------------
    # dtsg handling
    # ------------------------------------------------------------------

    def _get_fb_dtsg(self) -> str:
        """Return a cached dtsg token, fetching one from www.facebook.com if needed."""
        if self.fb_dtsg:
            return self.fb_dtsg

        self.progress("Fetching fb_dtsg ...")
        html = self.get("https://www.facebook.com").text

        m = re.search(r'\{"name":"fb_dtsg","value":"([^"]+)"\}', html)
        if not m:
            raise DtsgTokenFetchError("Could not find fb_dtsg")

        self.fb_dtsg = m.group(1)
        self._save_state()
        return self.fb_dtsg

    def _is_dtsg_invalid(self, response) -> bool:
        """Return True if the response says 'Sorry, something went wrong'."""
        text = response.text
        if not text.startswith("for (;;);"):
            return False
        try:
            data = json.loads(text.removeprefix("for (;;);"))
        except (json.JSONDecodeError, TypeError):
            return False
        return data.get("errorSummary") == "Sorry, something went wrong"

    def _extract_dtsg_from_response(self, response):
        """Return the dtsgToken from an error response, or None."""
        text = response.text
        if not text.startswith("for (;;);"):
            return None
        try:
            data = json.loads(text.removeprefix("for (;;);"))
        except (json.JSONDecodeError, TypeError):
            return None
        return data.get("dtsgToken")

    def _refresh_dtsg_from_response(self, response) -> bool:
        """Try to update the dtsg token from an error response. Returns True on success."""
        token = self._extract_dtsg_from_response(response)
        if token:
            self.fb_dtsg = token
            self._save_state()
            return True
        return False

    # ------------------------------------------------------------------
    # Doc-id resolution
    # ------------------------------------------------------------------

    def _resolve_doc_id(self, operation_name: str, reference_page_url: str) -> str:
        """
        Return the doc_id for the given operation, using caches where possible.
        Falls back to running the operation discovery flow.
        """
        # 1. global cache
        doc_id = self.operations.get(operation_name)
        if doc_id:
            return doc_id

        # 2. page cache
        page_ops = self.page_operations.get(reference_page_url) or {}
        doc_id = page_ops.get(operation_name)
        if doc_id:
            self.operations[operation_name] = doc_id
            self._save_state()
            return doc_id

        # 2b. page cache — scan every cached page for this operation
        # for cached_url, cached_ops in self.page_operations.items():
        #     doc_id = cached_ops.get(operation_name)
        #     if doc_id:
        #         logger.warning(
        #             f"Operation {operation_name!r} found on cached page "
        #             f"{cached_url!r} but not on {reference_page_url!r}; reusing."
        #         )
        #         self.operations[operation_name] = doc_id
        #         self._save_state()
        #         return doc_id

        # 3. discovery
        self.progress("Discovering doc_id ...")
        logger.info("Discovering doc_id for %s ...", operation_name)
        discovered = self.operation_discovery.discover_operation(reference_page_url, operation_name)

        # fill both caches
        self.page_operations[reference_page_url] = discovered

        doc_id = discovered.get(operation_name)
        if not doc_id:
            raise LookupError(
                f"Could not discover {operation_name!r} on {reference_page_url!r}"
            )
        self.operations[operation_name] = doc_id
        self._save_state()
        return doc_id

    def _invalidate_doc_id(self, operation_name: str, reference_page_url: str):
        """Drop a stale doc_id from both caches, and persist."""
        self.operations.pop(operation_name, None)
        page_ops = self.page_operations.get(reference_page_url)
        if page_ops:
            page_ops.pop(operation_name, None)
        self._save_state()

    def reload_cookies(self):
        """Re-read the cookies file into the current session."""
        self.session.cookies.clear()
        self._load_cookies()

    def get(self, url):
        """
        GET a Facebook HTML page as a browser navigation.

        Not a GraphQL request. Overrides the session's ``Accept`` header so Facebook returns the HTML page instead of an XHR/worker payload.

        :param url: Page URL to fetch.
        :type url: str
        :return: The HTTP response.
        :rtype: requests.Response
        """
        response = self.session.get(
            url,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            },
        )
        if self._check_session_dead(response):
            raise SessionExpiredError("Facebook Cookies are expired.")
        return response

    def post(self, operation_name, reference_page_url, variables, _retry=True):
        """
        Send a GraphQL request for the given operation.

        Looks up the doc_id (from cache or discovery), sends the full variables
        dict, and self-heals on doc-id rotation or dtsg rejection.
        """

        doc_id = self._resolve_doc_id(operation_name, reference_page_url)
        fb_dtsg = self._get_fb_dtsg()

        self.progress("Sending FacebookGql Request ...")
        logger.info("Sending FacebookGql Request (%s)", operation_name)

        payload = {
            "doc_id": doc_id,
            "variables": json.dumps(variables),
            "fb_dtsg": fb_dtsg,
            "__comet_req": 15,
            "__a": 1,
        }

        response = self.session.post(
            "https://web.facebook.com/api/graphql/", data=payload
        )
        if self._check_session_dead(response):
            raise SessionExpiredError("Facebook Cookies are expired.")

        if self.debug:
            self.debug_response(
                operation_name,
                doc_id,
                response,
            )

        reason = self._classify_error(response)

        # --- schema changed: not recoverable ---
        if reason == "schema":
            logger.error(
                "GraphQL schema changed for %s — variables no longer match",
                operation_name,
            )
            raise SchemaChangedError(
                f"Facebook GraphQL schema for {operation_name!r} required variables no longer match. "
                f"Check for a new update of facebook-gql-scraper, or open an issue: "
                f"https://github.com/XD-MHLOO/facebook-gql-scraper/issues"
            )

        # --- doc-id rotation ---
        if _retry and reason == "doc_id":
            self.progress("Facebook rotated the doc_id. Re-discovering ...")
            logger.info("doc_id invalid for %s", operation_name)
            self._invalidate_doc_id(operation_name, reference_page_url)

            retry_response = self.post(
                operation_name,
                reference_page_url,
                variables,
                _retry=False,
            )
            if self._classify_error(retry_response) == "doc_id":
                raise DocIdStillInvalidError(
                    f"'{operation_name}' doc id still invalid after re-discovery."
                )
            return retry_response

        # --- dtsg rejection ---
        if _retry and self._is_dtsg_invalid(response):
            self.progress("Refreshing fb_dtsg token ...")
            logger.info("Facebook rejected fb_dtsg, refreshing from error response")

            if self._refresh_dtsg_from_response(response):
                retry_response = self.post(
                    operation_name,
                    reference_page_url,
                    variables,
                    _retry=False,
                )

                if self._is_dtsg_invalid(retry_response):
                    raise DtsgTokenStillInvalidError(
                        "still invalid after using a new fb_dstg token."
                    )
                return retry_response
            else:
                raise DtsgTokenFetchError("Failed to refetch a new fb_dtsg token.")
        return response

    def parse_graphql_response(self, raw):
        obj = consolidate_jsonl(raw)

        if obj is None:
            return None

        parsed = parse_facebook_payload(obj)

        if parsed is None:
            return None

        return parsed

    # ------------------------------------------------------------------
    # Debug saving
    # ------------------------------------------------------------------

    def debug_response(self, operation_name, doc_id, response):
        """Save a GraphQL response together with request/response information."""

        os.makedirs(self.debug_dir, exist_ok=True)

        filepath_raw = os.path.join(
            self.debug_dir, f"{operation_name}_{doc_id}_raw.txt"
        )
        with open(filepath_raw, "w", encoding="utf-8") as f:
            f.write(response.text)

        post_data = response.request.body or ""

        from urllib.parse import parse_qs

        # requests may give us bytes here
        if isinstance(post_data, bytes):
            post_data = post_data.decode("utf-8", errors="replace")

        form = parse_qs(post_data, keep_blank_values=True)

        variables_raw = form.get("variables", [None])[0]

        try:
            variables = json.loads(variables_raw) if variables_raw else None
        except json.JSONDecodeError:
            variables = variables_raw

        consolidated_json = consolidate_jsonl(response.text)

        filepath_consolidated = os.path.join(
            self.debug_dir, f"{operation_name}_{doc_id}_consolidated.json"
        )
        with open(filepath_consolidated, "w", encoding="utf-8") as f:
            json.dump(consolidated_json, f, indent=2, ensure_ascii=False)

        parsed = None

        if consolidated_json is not None:
            # ---- 4. Noise removal (only if consolidate succeeded) ----
            noise_removed_json = remove_raw_facebook_json_noise(consolidated_json)
            filepath_cleaned = os.path.join(
                self.debug_dir, f"{operation_name}_{doc_id}_cleaned.json"
            )
            with open(filepath_cleaned, "w", encoding="utf-8") as f:
                json.dump(noise_removed_json, f, indent=2, ensure_ascii=False)

            # ---- 5. Parse (only if consolidate succeeded) ----
            parsed = parse_facebook_payload(consolidated_json)
        else:
            logger.warning(
                "Failed to consolidate (%s); saving request/response only.", operation_name
            )

        debug_data = {
            "request": {
                "url": response.request.url,
                "method": response.request.method,
                "headers": dict(response.request.headers),
                "cookies": self.session.cookies.get_dict(),
                "body": response.request.body if response.request.body else None,
                "variables": variables,
            },
            "response": {
                "status_code": response.status_code,
                "reason": response.reason,
                "url": response.url,
                "headers": dict(response.headers),
                "parsed": parsed,
            },
        }

        filepath_parsed = os.path.join(
            self.debug_dir, f"{operation_name}_{doc_id}_parsed.json"
        )
        with open(filepath_parsed, "w", encoding="utf-8") as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)

        logger.info("GraphQL debug data saved: %s", filepath_parsed)


class FacebookGraphQL:
    OPERATION_NAME: str = None
    REFERENCE_PAGE_URL: str = None
    VARIABLES: dict = None

    def __init__(self, context: FacebookContext):
        self.context = context

    def send(self, variables):
        return self.context.post(
            operation_name=self.OPERATION_NAME,
            reference_page_url=self.REFERENCE_PAGE_URL,
            variables=variables,
        )


class ProfileCometAboutAppSectionQueryGraphQL(FacebookGraphQL):
    """Profile About tab — sections and collections for a user's About page."""

    OPERATION_NAME = "ProfileCometAboutAppSectionQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://web.facebook.com/Cristiano/about"
    VARIABLES = {
        "appSectionFeedKey": None,
        "collectionToken": None,
        "pageID": None,
        "rawSectionToken": None,
        "scale": 1,
        "sectionToken": None,
        "showReactions": True,
        "userID": None,
        "__relay_internal__pv__FBProfile_enable_perf_improv_gkrelayprovider": True,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometReels_enable_e2e_logging_gkrelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaContentContainer_comet_video_document_picture_in_picture_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaContentContainer_enable_chapters_pill_gkrelayprovider": True,
        "__relay_internal__pv__ShouldEnableBakedInTextUnifiedVideorelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoCometVideoMedia_comet_photosensitive_content_warning_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaHeaderControls_enable_chapters_pill_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_organic_ad_cta_on_comet_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_meta_ai_pill_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_ai_embodiment_chat_pill_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_video_augment_pills_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoPlayerScrubber_fb_comet_vpv_heatmap_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoDescriptionWithEntities_comet_translations_revamp_sync_caption_with_audio_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoFeedbackBar_comet_reels_save_button_gkrelayprovider": False,
        "__relay_internal__pv__usePushPipEngagementCounts_comet_video_document_picture_in_picture_gkrelayprovider": False,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMenu_fb_reels_ranking_debug_tool_gkrelayprovider": False,
        "__relay_internal__pv__CometAudioLanguageUtils_comet_translations_revamp_preferred_languages_gkrelayprovider": False,
    }

    def send(self, userId: str, sectionToken: str, collectionToken: str):
        variables = dict(self.VARIABLES)
        variables["userID"] = userId
        variables["pageID"] = userId
        variables["sectionToken"] = sectionToken
        variables["collectionToken"] = collectionToken
        return super().send(variables)


class ProfileCometHeaderQueryGraphQL(FacebookGraphQL):
    """
    Profile header — basic profile info and the collection IDs used to
    navigate the user's profile tabs (About, Followers, Photos, Reels, etc.).
    """

    OPERATION_NAME = "ProfileCometHeaderQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano"
    VARIABLES = {
        "scale": 1,
        "selectedID": None,
        "selectedSpaceType": "profile",
        "shouldUseFXIMProfilePicEditor": False,
        "userID": None,
    }

    def send(self, userId: str):
        variables = dict(self.VARIABLES)
        variables["userID"] = userId
        variables["selectedID"] = userId
        return super().send(variables)


class ProfileCometAppCollectionListRendererPaginationQueryGraphQL(FacebookGraphQL):
    """Timeline app collection — followers, followees, friends, or photos, paginated."""

    OPERATION_NAME = (
        "ProfileCometAppCollectionListRendererPaginationQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/followers"
    VARIABLES = {
        "count": 8,
        "cursor": None,
        "scale": 1,
        "search": None,
        "id": None,
        "__relay_internal__pv__FBProfile_enable_perf_improv_gkrelayprovider": True,
    }

    def send(self, collectionId: str, cursor: str = None):
        variables = dict(self.VARIABLES)
        variables["id"] = collectionId
        variables["cursor"] = cursor
        return super().send(variables)


class ProfileCometAppCollectionReelsRendererPaginationQueryGraphQL(FacebookGraphQL):
    """Timeline app collection — reels with fuller video metadata, paginated."""

    OPERATION_NAME = (
        "ProfileCometAppCollectionReelsRendererPaginationQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/reels/"
    VARIABLES = {
        "count": 10,
        "cursor": None,
        "renderLocation": None,
        "scale": 1,
        "useDefaultActor": False,
        "id": None,
        "__relay_internal__pv__CometReels_enable_e2e_logging_gkrelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaContentContainer_comet_video_document_picture_in_picture_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaContentContainer_enable_chapters_pill_gkrelayprovider": True,
        "__relay_internal__pv__ShouldEnableBakedInTextUnifiedVideorelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoCometVideoMedia_comet_photosensitive_content_warning_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaHeaderControls_enable_chapters_pill_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_organic_ad_cta_on_comet_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_meta_ai_pill_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_ai_embodiment_chat_pill_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoMediaFooter_enable_video_augment_pills_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoPlayerScrubber_fb_comet_vpv_heatmap_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoDescriptionWithEntities_comet_translations_revamp_sync_caption_with_audio_gkrelayprovider": False,
        "__relay_internal__pv__FBUnifiedVideoFeedbackBar_comet_reels_save_button_gkrelayprovider": False,
        "__relay_internal__pv__usePushPipEngagementCounts_comet_video_document_picture_in_picture_gkrelayprovider": False,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__FBUnifiedVideoMenu_fb_reels_ranking_debug_tool_gkrelayprovider": False,
        "__relay_internal__pv__CometAudioLanguageUtils_comet_translations_revamp_preferred_languages_gkrelayprovider": False,
    }

    def send(self, collectionId: str, cursor: str = None):
        variables = dict(self.VARIABLES)
        variables["id"] = collectionId
        variables["cursor"] = cursor
        return super().send(variables)


class ProfileCometTimelineFeedRefetchQueryGraphQL(FacebookGraphQL):
    """Profile timeline — the user's own posts, paginated."""

    OPERATION_NAME = "ProfileCometTimelineFeedRefetchQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano"
    VARIABLES = {
        "afterTime": None,
        "beforeTime": None,
        "count": 2,
        "cursor": None,
        "feedLocation": "TIMELINE",
        "feedbackSource": 0,
        "focusCommentID": None,
        "id": None,
        "memorializedSplitTimeFilter": None,
        "omitPinnedPost": True,
        "postedBy": {"group": "OWNER"},
        "privacy": None,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "referringStoryRenderLocation": None,
        "renderLocation": "timeline",
        "run_with_continuation_key": True,
        "scale": 1,
        "stream_count": 1,
        "taggedInOnly": None,
        "trackingCode": None,
        "useDefaultActor": False,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
        "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
        "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
        "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
        "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
        "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
        "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
        "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
        "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    }

    def send(
        self,
        userId: str,
        cursor: str = None,
        afterTime: str = None,
        beforeTime: str = None,
    ):
        variables = dict(self.VARIABLES)
        variables["id"] = userId
        variables["cursor"] = cursor
        if afterTime is not None:
            dt = datetime.strptime(afterTime, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            variables["afterTime"] = int(dt.timestamp())
        if beforeTime is not None:
            dt = datetime.strptime(beforeTime, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            variables["beforeTime"] = int(dt.timestamp())
        return super().send(variables)


class CometSinglePostDialogContentQueryGraphQL(FacebookGraphQL):
    """Single post detail — full post content, comments, reactions."""

    OPERATION_NAME = "CometSinglePostDialogContentQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/posts/pfbid02wwWW6zEYdHpCmYbVWEwJMX8QH5ve4izADrhZpPeHxFScJkwEbdLsq9VpoboHpJFLl"
    VARIABLES = {
        "feedbackSource": 2,
        "feedLocation": "POST_PERMALINK_DIALOG",
        "focusCommentID": None,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "renderLocation": "permalink",
        "scale": 1,
        "shouldChangeNodeFieldName": True,
        "storyID": None,
        "useDefaultActor": False,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
        "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
        "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
        "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
        "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
        "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
        "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
        "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
        "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
        "__relay_internal__pv__ProfileCometSeoIsViewerLoggedOutrelayprovider": False,
        "__relay_internal__pv__CometSinglePostDialogContent_isFloatingCTAEnabledrelayprovider": False,
    }

    def send(self, postId: str, postType: Literal["user_post", "group_post"]= "user_post", userId: str = "1"):
        variables = dict(self.VARIABLES)
        if postType == "user_post":
            story_id = f"S:_I{userId}:{postId}:{postId}"
            variables["referringStoryRenderLocation"] = "timeline"
        elif postType == "group_post":
            story_id = f"S:_I{userId}:VK:{postId}"
            variables["referringStoryRenderLocation"] = "group"
        else:
            raise ValueError(f"Unknown post type: {postType!r}")
        variables["storyID"] = base64.b64encode(story_id.encode()).decode()
        return super().send(variables)


class CommentsListComponentsPaginationQueryGraphQL(FacebookGraphQL):
    """Post comments — top-level comments, paginated."""

    OPERATION_NAME = "CommentsListComponentsPaginationQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/posts/pfbid02wwWW6zEYdHpCmYbVWEwJMX8QH5ve4izADrhZpPeHxFScJkwEbdLsq9VpoboHpJFLl"
    VARIABLES = {
        "commentsAfterCount": None,
        "commentsAfterCursor": None,
        "commentsBeforeCount": None,
        "commentsBeforeCursor": None,
        "commentsIntentToken": None,
        "feedLocation": "POST_PERMALINK_DIALOG",
        "focusCommentID": None,
        "id": None,
        "scale": 1,
        "targetDialect": None,
        "useDefaultActor": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
    }

    def send(self, postId: str, commentsAfterCursor: str = None):
        variables = dict(self.VARIABLES)
        variables["id"] = base64.b64encode(f"feedback:{postId}".encode()).decode()
        if commentsAfterCursor is not None:
            variables["commentsAfterCount"] = -1
            variables["commentsAfterCursor"] = commentsAfterCursor
        return super().send(variables)


class Depth1CommentsListPaginationQueryGraphQL(FacebookGraphQL):
    """Comment replies — first-level replies to a comment, paginated."""

    OPERATION_NAME = "Depth1CommentsListPaginationQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/posts/pfbid02wwWW6zEYdHpCmYbVWEwJMX8QH5ve4izADrhZpPeHxFScJkwEbdLsq9VpoboHpJFLl"
    VARIABLES = {
        "clientKey": None,
        "expansionToken": None,
        "feedLocation": "POST_PERMALINK_DIALOG",
        "focusCommentID": None,
        "id": None,
        "repliesAfterCount": None,
        "repliesAfterCursor": None,
        "repliesBeforeCount": None,
        "repliesBeforeCursor": None,
        "scale": 1,
        "useDefaultActor": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
    }

    def send(
        self,
        postId: str,
        commentId: str,
        expansionToken: str,
        repliesAfterCursor: str = None,
    ):
        variables = dict(self.VARIABLES)
        variables["id"] = base64.b64encode(
            f"feedback:{postId}_{commentId}".encode()
        ).decode()
        variables["expansionToken"] = expansionToken
        variables["focusCommentID"] = commentId
        if repliesAfterCursor is not None:
            variables["repliesAfterCount"] = -1
            variables["repliesAfterCursor"] = repliesAfterCursor
        return super().send(variables)


class Depth2CommentsListPaginationQueryGraphQL(FacebookGraphQL):
    """Comment sub-replies — second-level replies, paginated."""

    OPERATION_NAME = "Depth2CommentsListPaginationQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/posts/pfbid02wwWW6zEYdHpCmYbVWEwJMX8QH5ve4izADrhZpPeHxFScJkwEbdLsq9VpoboHpJFLl"
    VARIABLES = {
        "clientKey": None,
        "expansionToken": None,
        "feedLocation": "POST_PERMALINK_DIALOG",
        "id": None,
        "scale": 1,
        "subRepliesAfterCount": None,
        "subRepliesAfterCursor": None,
        "subRepliesBeforeCount": None,
        "subRepliesBeforeCursor": None,
        "useDefaultActor": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
    }

    def send(
        self,
        postId: str,
        commentId: str,
        expansionToken: str,
        subRepliesAfterCursor: str = None,
    ):
        variables = dict(self.VARIABLES)
        variables["id"] = base64.b64encode(
            f"feedback:{postId}_{commentId}".encode()
        ).decode()
        variables["expansionToken"] = expansionToken
        if subRepliesAfterCursor is not None:
            variables["subRepliesAfterCount"] = -1
            variables["subRepliesAfterCursor"] = subRepliesAfterCursor
        return super().send(variables)


class CometUFIReactionsDialogTabContentRefetchQueryGraphQL(FacebookGraphQL):
    """Post and comment reactors — list of users who reacted, paginated."""

    OPERATION_NAME = (
        "CometUFIReactionsDialogTabContentRefetchQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = "https://web.facebook.com/ufi/reaction/profile/browser/?ft_ent_identifier=1477237711067526"
    VARIABLES = {
        "count": 10,
        "cursor": None,
        "feedbackTargetID": None,
        "id": None,
        "reactionID": None,
        "scale": 1,
    }

    def send(
        self,
        postId: str,
        reactionID: str = None,
        cursor: str = None,
        commentId: str = None,
        itemType="post",
    ):
        variables = dict(self.VARIABLES)
        target_id = (
            f"feedback:{postId}" if itemType == "post" else f"feedback:{postId}_{commentId}"
        )
        encoded = base64.b64encode(target_id.encode()).decode()
        variables["feedbackTargetID"] = encoded
        variables["id"] = encoded
        if reactionID is not None:
            variables["reactionID"] = reactionID
        if cursor is not None:
            variables["cursor"] = cursor
        return super().send(variables)


class CometHovercardQueryRendererQueryGraphQL(FacebookGraphQL):
    """Profile or group hovercard — lightweight summary card."""

    OPERATION_NAME = "CometHovercardQueryRendererQuery$Parameters"
    REFERENCE_PAGE_URL = "https://www.facebook.com/Cristiano/about"
    VARIABLES = {
        "actionBarRenderLocation": "WWW_COMET_HOVERCARD",
        "context": "GROUP",
        "entityID": None,
        "groupID": None,
        "scale": 1,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
    }

    def send(self, groupId: str):
        variables = dict(self.VARIABLES)
        variables["entityID"] = groupId
        variables["groupID"] = groupId
        return super().send(variables)


class CometGroupAboutRootQueryGraphQL(FacebookGraphQL):
    """Group About page — description, privacy, member count, created time."""

    OPERATION_NAME = "CometGroupAboutRootQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/groups/workingmemes/about"
    VARIABLES = {"groupID": None, "scale": 1}

    def send(self, groupId: str):
        variables = dict(self.VARIABLES)
        variables["groupID"] = groupId
        return super().send(variables)


class GroupsCometFeedRegularStoriesPaginationQueryGraphQL(FacebookGraphQL):
    """Group timeline — posts within a group, paginated."""

    OPERATION_NAME = (
        "GroupsCometFeedRegularStoriesPaginationQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = "https://www.facebook.com/groups/workingmemes"
    VARIABLES = {
        "count": 3,
        "cursor": None,
        "feedLocation": "GROUP",
        "feedType": "DISCUSSION",
        "feedbackSource": 0,
        "filterTopicId": None,
        "focusCommentID": None,
        "id": None,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "referringStoryRenderLocation": None,
        "renderLocation": "group",
        "scale": 1,
        "sortingSetting": "CHRONOLOGICAL",
        "stream_initial_count": 1,
        "useDefaultActor": False,
        "youthIntegrityHostID": None,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
        "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
        "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
        "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
        "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
        "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
        "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
        "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
        "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    }

    def send(self, groupId: str, cursor: str, sortingSetting: str = "CHRONOLOGICAL"):
        variables = dict(self.VARIABLES)
        variables["id"] = groupId
        variables["youthIntegrityHostID"] = groupId
        variables["sortingSetting"] = sortingSetting
        variables["cursor"] = cursor
        return super().send(variables)


class GroupsCometMembersPageNewMembersSectionRefetchQueryGraphQL(FacebookGraphQL):
    """Group members — list of members, paginated."""

    OPERATION_NAME = (
        "GroupsCometMembersPageNewMembersSectionRefetchQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = "https://www.facebook.com/groups/workingmemes/members"
    VARIABLES = {
        "count": 10,
        "cursor": None,
        "groupID": None,
        "id": None,
        "recruitingGroupFilterNonCompliant": False,
        "scale": 1,
    }

    def send(self, groupId: str, cursor: str = None):
        variables = dict(self.VARIABLES)
        variables["groupID"] = groupId
        variables["id"] = groupId
        variables["cursor"] = cursor
        return super().send(variables)


class SearchCometResultsPaginatedResultsQueryGraphQL(FacebookGraphQL):
    """Facebook SERP — profiles, posts, and groups matching a search query, paginated."""

    OPERATION_NAME = "SearchCometResultsPaginatedResultsQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/search/people/?q=Ishowspeed"
    VARIABLES = {
        "allow_streaming": False,
        "args": {
            "callsite": "COMET_GLOBAL_SEARCH",
            "config": {
                "exact_match": False,
                "high_confidence_config": None,
                "intercept_config": None,
                "sts_disambiguation": None,
                "watch_config": None,
            },
            "context": {"bsid": None, "tsid": None},
            "experience": {
                "client_defined_experiences": ["ADS_PARALLEL_FETCH"],
                "encoded_server_defined_params": None,
                "fbid": None,
                "type": "PEOPLE_TAB",
            },
            "filters": [],
            "text": None,
        },
        "count": 5,
        "cursor": None,
        "feedLocation": "SEARCH",
        "feedbackSource": 23,
        "fetch_filters": True,
        "focusCommentID": None,
        "locale": None,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "referringStoryRenderLocation": None,
        "renderLocation": "search_results_page",
        "scale": 1,
        "stream_initial_count": 0,
        "useDefaultActor": False,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider": False,
        "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
        "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
        "__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider": True,
        "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
        "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
        "__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider": True,
        "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
        "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
        "__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider": False,
        "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
        "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
    }

    def send(
        self,
        text: str = "",
        filter_type: str = "all",
        exact_match: bool = False,
        cursor: str = None,
    ):
        variables = dict(self.VARIABLES)
        exp_type = "GLOBAL_SEARCH"
        filters = []
        if filter_type == "profile":
            exp_type = "PEOPLE_TAB"
        elif filter_type == "group":
            exp_type = "GROUPS_TAB"
        elif filter_type == "post":
            filters = ['{"name":"merged_public_posts","args":""}']
        variables["args"] = {
            **self.VARIABLES["args"],
            "config": {**self.VARIABLES["args"]["config"], "exact_match": exact_match},
            "experience": {**self.VARIABLES["args"]["experience"], "type": exp_type},
            "filters": filters,
            "text": text,
        }
        variables["cursor"] = cursor
        return super().send(variables)


class CometMarketplaceSearchContentPaginationQueryGraphQL(FacebookGraphQL):
    """Marketplace search — listings matching a query, paginated."""

    OPERATION_NAME = (
        "CometMarketplaceSearchContentPaginationQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = (
        "https://www.facebook.com/marketplace/160300197351040/search/?query=67"
    )
    VARIABLES = {
        "count": 24,
        "cursor": None,
        "params": {
            "bqf": {"callsite": "COMMERCE_MKTPLACE_WWW", "query": None},
            "browse_request_params": {
                "commerce_enable_local_pickup": True,
                "commerce_enable_shipping": True,
                "commerce_search_and_rp_available": True,
                "commerce_search_and_rp_category_id": [],
                "commerce_search_and_rp_condition": None,
                "commerce_search_and_rp_ctime_days": None,
                "filter_location_latitude": 35.656091,
                "filter_location_longitude": 139.736009,
                "filter_price_lower_bound": 0,
                "filter_price_upper_bound": 214748364700,
                "filter_radius_km": 500,
            },
            "custom_request_params": {
                "browse_context": None,
                "contextual_filters": [],
                "referral_code": None,
                "referral_ui_component": None,
                "saved_search_strid": None,
                "search_vertical": "C2C",
                "seo_url": None,
                "serp_landing_settings": {"virtual_category_id": ""},
                "surface": "SEARCH",
                "virtual_contextual_filters": [],
            },
        },
        "scale": 1,
        "__relay_internal__pv__GHLShouldChangeMarketplaceSponsoredDataFieldNamerelayprovider": True,
    }

    def send(
        self,
        query: str,
        cursor: str = None,
        is_stock_available: bool = True,
        filter_location_latitude: float = 40.7128,
        filter_location_longitude: float = -74.0060,
        filter_price_lower_bound: int = 0,
        filter_price_upper_bound: int = 2147483647,
        filter_radius_km: int = 500,
        item_condition: str = None,  # new, used_like_new, used_good, used_fair,
        last_n_days: int = None,
        sort_by: str = None,  # PRICE_DESCEND, PRICE_ASCEND, CREATION_TIME_DESCEND, DISTANCE_ASCEND
    ):

        commerce_search_and_rp_ctime_days = None
        if last_n_days:
            today_utc = datetime.now(timezone.utc).date()
            ids = [
                (today_utc - timedelta(days=i) - date(1970, 1, 1)).days
                for i in range(last_n_days + 1)
            ]
            commerce_search_and_rp_ctime_days = ";".join(str(i) for i in ids)

        variables = dict(self.VARIABLES)
        variables["cursor"] = cursor
        variables["params"] = {
            **self.VARIABLES["params"],
            "bqf": {
                **self.VARIABLES["params"]["bqf"],
                "query": query,
            },
            "browse_request_params": {
                **self.VARIABLES["params"]["browse_request_params"],
                "commerce_search_and_rp_available": is_stock_available,
                "commerce_search_and_rp_condition": item_condition,
                "commerce_search_and_rp_ctime_days": commerce_search_and_rp_ctime_days,
                "filter_location_latitude": filter_location_latitude,
                "filter_location_longitude": filter_location_longitude,
                "filter_price_lower_bound": filter_price_lower_bound * 100,
                "filter_price_upper_bound": filter_price_upper_bound * 100,
                "filter_radius_km": filter_radius_km,
            },
        }
        if sort_by is not None:
            variables["params"]["browse_request_params"]["commerce_search_sort_by"] = (
                sort_by
            )

        return super().send(variables)


class MarketplacePDPContainerQueryGraphQL(FacebookGraphQL):
    """Marketplace product details page — listing fields and seller context."""

    OPERATION_NAME = "MarketplacePDPContainerQuery_facebookRelayOperation"
    REFERENCE_PAGE_URL = "https://www.facebook.com/ajax/bootloader-endpoint/?modules=CometMarketplacePermalinkRoot.react"
    VARIABLES = {
        "enableJobEmployerActionBar": False,
        "enableJobSeekerActionBar": False,
        "feedbackSource": 56,
        "feedLocation": "MARKETPLACE_MEGAMALL",
        "referralCode": "null",
        "referralSurfaceString": "search",
        "scale": 1,
        "shouldFetchLoggedOutSimilarListings": False,
        "targetId": None,
        "useDefaultActor": False,
        "__relay_internal__pv__MarketplacePDPCometSimilarListingsrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPShouldShowRelatedSearchesrelayprovider": True,
        "__relay_internal__pv__MarketplacePDPShouldShowLoggedOutSellerTrustrelayprovider": False,
        "__relay_internal__pv__ShouldUpdateMarketplaceBoostListingBoostedStatusrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPIsLoggedOutrelayprovider": False,
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
        "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
        "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
        "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": True,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
        "__relay_internal__pv__MarketplacePDPShouldShowBSGRecommendationsrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPJobShouldShowSharedGroupsSectionrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPJobIsShareToGroupsEnabledOnCometrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPShouldShowFAQrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPShouldShowRelatedCategoriesrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPShouldShowSupportFooterrelayprovider": False,
        "__relay_internal__pv__MarketplacePDPShouldUseListingRevamprelayprovider": False,
    }

    def send(self, marketListingId: str):
        variables = dict(self.VARIABLES)
        variables["targetId"] = marketListingId
        return super().send(variables)


class MarketplacePDPC2CMediaViewerWithImagesQueryGraphQL(FacebookGraphQL):
    """Marketplace PDP media — photos and videos for a listing."""

    OPERATION_NAME = (
        "MarketplacePDPC2CMediaViewerWithImagesQuery_facebookRelayOperation"
    )
    REFERENCE_PAGE_URL = (
        "https://www.facebook.com/marketplace/160300197351040/search/?query=67"
    )
    VARIABLES = {"targetId": None}

    def send(self, marketListingId: str):
        variables = dict(self.VARIABLES)
        variables["targetId"] = marketListingId
        return super().send(variables)
