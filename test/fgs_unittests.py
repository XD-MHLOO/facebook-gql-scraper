import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

import unittest
import facebook_gql_scraper as fgs


# ============================================================
# Test constants
# ============================================================

PROFILE_ID = "100044296486382"
# FRIENDS_PROFILE_ID = "123"

POST_ID = "2397851114308533"
COMMENT_ID = "2398004820959829"

GROUP_ID = "2781022932139267"

MAX_POSTS = 10
MAX_PHOTOS = 10
MAX_VIDEOS = 10
MAX_FOLLOWEES = 50
MAX_FOLLOWERS = 50
MAX_FRIENDS_FOLLOWEES = 50
MAX_FRIENDS_FOLLOWERS = 50
MAX_COMMENTS = 50
MAX_REACTORS = 50
MAX_GROUP_MEMBERS = 50
MAX_GROUP_POSTS = 10
MAX_SEARCH_RESULTS = 10
MAX_MARKETPLACE_RESULTS = 10


class TestFacebook(unittest.TestCase):

    def setUp(self):
        self.fbContext = fgs.FacebookContext(debug=True)

    # ========================================================
    # Profile
    # ========================================================

    def test_profile(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, PROFILE_ID)

    def test_profile_posts(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)

        posts = []
        for i, post in enumerate(user.get_posts()):
            posts.append(post)
            if i >= MAX_POSTS - 1:
                break

        self.assertTrue(len(posts) > 0)

    def test_profile_photos(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)

        photos = []
        for i, photo in enumerate(user.get_photos()):
            photos.append(photo)
            if i >= MAX_PHOTOS - 1:
                break

        self.assertTrue(len(photos) > 0)

    def test_profile_videos(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)

        videos = []
        for i, video in enumerate(user.get_videos()):
            videos.append(video)
            if i >= MAX_VIDEOS - 1:
                break

        self.assertTrue(len(videos) > 0)

    def test_profile_followees(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)

        followees = []
        for i, followee in enumerate(user.get_followees()):
            followees.append(followee)
            if i >= MAX_FOLLOWEES - 1:
                break

        self.assertTrue(len(followees) > 0)

    def test_profile_followers(self):
        user = fgs.Profile.from_id(self.fbContext, id=PROFILE_ID)

        followers = []
        for i, follower in enumerate(user.get_followers()):
            followers.append(follower)
            if i >= MAX_FOLLOWERS - 1:
                break

        self.assertTrue(len(followers) > 0)

    # def test_friends_followees(self):
    #     user = fgs.Profile.from_id(self.fbContext, id=FRIENDS_PROFILE_ID)

    #     followees = []
    #     for i, followee in enumerate(user.get_friends_followees()):
    #         followees.append(followee)
    #         if i >= MAX_FRIENDS_FOLLOWEES - 1:
    #             break

    #     self.assertTrue(len(followees) > 0)

    # def test_friends_followers(self):
    #     user = fgs.Profile.from_id(self.fbContext, id=FRIENDS_PROFILE_ID)

    #     followers = []
    #     for i, follower in enumerate(user.get_friends_followers()):
    #         followers.append(follower)
    #         if i >= MAX_FRIENDS_FOLLOWERS - 1:
    #             break

    #     self.assertTrue(len(followers) > 0)

    # ========================================================
    # Post
    # ========================================================

    def test_post(self):
        post = fgs.Post.from_id(self.fbContext, id=POST_ID)
        self.assertIsNotNone(post)
        self.assertEqual(post.id, POST_ID)

    def test_post_comments(self):
        post = fgs.Post.from_id(self.fbContext, id=POST_ID)

        comments = []
        for i, comment in enumerate(post.get_comments()):
            comments.append(comment)
            if i >= MAX_COMMENTS - 1:
                break

        self.assertTrue(len(comments) > 0)

    def test_post_reactors(self):
        post = fgs.Post.from_id(self.fbContext, id=POST_ID)

        reactors = []
        for i, reactor in enumerate(post.get_reactors()):
            reactors.append(reactor)
            if i >= MAX_REACTORS - 1:
                break

        self.assertTrue(len(reactors) > 0)

    # ========================================================
    # Comment
    # ========================================================

    def test_comment_reactors_and_replies(self):
        post = fgs.Post.from_id(self.fbContext, id=POST_ID)

        found_comment = False
        reactors = []
        replies = []
        subreplies = []

        for comment in post.get_comments():
            if comment.id == COMMENT_ID:
                found_comment = True

                for i, reactor in enumerate(comment.get_reactors()):
                    reactors.append(reactor)
                    if i >= MAX_REACTORS - 1:
                        break

                # for comment_reply in comment.get_replies():
                #     replies.append(comment_reply)
                #     for comment_subreply in comment_reply.get_replies():
                #         subreplies.append(comment_subreply)
                break

        self.assertTrue(found_comment)
        self.assertIsNotNone(reactors)
        # self.assertIsNotNone(replies)
        # self.assertIsNotNone(subreplies)

    # ========================================================
    # Group
    # ========================================================

    def test_group(self):
        group = fgs.Group.from_id(self.fbContext, id=GROUP_ID)
        self.assertIsNotNone(group)
        self.assertEqual(group.id, GROUP_ID)

    def test_group_members(self):
        group = fgs.Group.from_id(self.fbContext, id=GROUP_ID)

        members = []
        for i, member in enumerate(group.get_members()):
            members.append(member)
            if i >= MAX_GROUP_MEMBERS - 1:
                break

        self.assertTrue(len(members) > 0)

    def test_group_posts(self):
        group = fgs.Group.from_id(self.fbContext, id=GROUP_ID)

        posts = []
        for i, post in enumerate(group.get_posts()):
            posts.append(post)
            if i >= MAX_GROUP_POSTS - 1:
                break

        self.assertTrue(len(posts) > 0)

    # ========================================================
    # Search
    # ========================================================

    def test_search(self):
        engine = fgs.SearchEngine(self.fbContext)

        results = []
        for i, item in enumerate(engine.search("facebook")):
            results.append(item)
            if i >= MAX_SEARCH_RESULTS - 1:
                break

        self.assertTrue(len(results) > 0)

    # ========================================================
    # Marketplace
    # ========================================================

    def test_search_marketplace(self):
        engine = fgs.SearchEngine(self.fbContext)

        results = []
        for i, listing in enumerate(
            engine.search_marketplace("iphone", is_stock_available=True)
        ):
            results.append(listing)
            if i >= MAX_MARKETPLACE_RESULTS - 1:
                break

        if not results:
            self.skipTest("Marketplace search returned no results.")

        for listing in results:
            self.assertIsInstance(listing, fgs.MarketplaceListing)
            self.assertIsNotNone(listing.id)

    def test_marketplace_listing(self):
        """Discover a live listing via search, then load it via from_id()."""
        engine = fgs.SearchEngine(self.fbContext)

        listing_id = None
        for listing in engine.search_marketplace("iphone", is_stock_available=True):
            if listing.id:
                listing_id = listing.id
                break

        if listing_id is None:
            self.skipTest("No live Marketplace listing available.")

        listing = fgs.MarketplaceListing.from_id(
            self.fbContext, id=listing_id
        )

        self.assertIsNotNone(listing)
        self.assertEqual(listing.id, listing_id)


if __name__ == "__main__":
    unittest.main()