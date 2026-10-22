# Facebook GraphQL Scraper

Scrape Facebook GraphQL data without an API key — profiles, posts, comments, reactions, groups, marketplace, search_engine.

Inspired by [facebook-graphql-scraper](https://github.com/FaustRen/facebook-graphql-scraper).
> I couldn't find a free Facebook scraper that was still working, so I decided to build one :)

---

The scraper is designed to be fast, lightweight, and reliable.

- **GraphQL-based:** Fetches data directly through Facebook's internal GraphQL endpoints.
- **No HTML parsing or CSS selectors:** Avoids brittle UI-dependent scraping that can break when Facebook changes its layout.
- **No headless browser or browser automation:** Reduces resource usage by avoiding the overhead of running a full browser.

When Facebook updates its GraphQL operation Doc IDs, the scraper automatically rediscovers them using a lightweight JavaScript runtime powered by V8 [PyMiniRacer](https://github.com/bpcreech/PyMiniRacer).

```

           Facebook Gql Scraper
                    │
                    ▼
              ┌───────────┐
              │  Doc ID   │◄──────────────┐
              └─────┬─────┘               │
                    │                     │
                    ▼                     │
              GraphQL Request             │
                    │                     │
              ┌─────┴─────────┐           │
              │               │           │
        [Doc Id Valid]  [Doc Id Invalid]  │
              │               │           │
              ▼               ▼           │
           Scrape       Mini JavaScript   │
                              V8          │
                              │           │
                              ▼           │
                           New Doc ID ────┘
```

See the full [Documentation](https://XD-MHLOO.github.io/facebook-gql-scraper/)

---

## Installation

```bash
pip install facebook-gql-scraper
```
---

## Quick start

Export your Facebook session cookies as JSON and save them as
`facebook_cookies.json` in your working directory.

- Firefox: [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
- Windows: [EditThisCookie (V3)](https://chromewebstore.google.com/detail/ojfebgpkimhlhcblbalbfjblapadhbol?utm_source=item-share-cb)

## Profile

```python
import facebook_gql_scraper as fgs

ctx = fgs.FacebookContext(cookies_file="facebook_cookies.json")
user = fgs.Profile.from_user_id(ctx, user_id="100084254631043")
# Or from username: user = fgs.Profile.from_username(ctx, username="Ishowspeed")
print(user.name)
```
> Pass `quiet=True` to `FacebookContext` to hide logs.
### Profile properties

```python
## Identity/ Social
user.id                 # "123"
user.name               # "John Doe"
user.alternate_name     # "john donut"
user.gender             # "MALE"
user.url                # "https://www.facebook.com/johndoe"
user.status_text        # "La peace"
user.profile_picture_url # "https://scontent...jpg"
user.is_verified        # False

user.followers_count    # '123'
user.following_count    # '6.9k'
user.friends_count      # '4'

## About / bio
user.biography          # "Thank God👏🏽🙏🏽"
user.category           # "Gaming video creator"
user.description        # "desc"
user.current_location   # "La Peace"
user.hometown           # "Cincinnati, Ohio, USA"
user.birthday           # "21 January 2005"

user.relationship       # {"type": "Married", "date": "12 June 2019", "desc": "with Jane Doe"}

user.family             # [
                        #     {"name": "Jane Doe", "type": "Wife"},
                        #     {"name": "John Dad", "type": "Father"},
                        # ]

user.language           # ["English", "Spanish"]
user.links              # [{"link": "speed.store", "desc": "speed.store"}]
user.works              # [{"company": "Minecraft", "desc": "Senior | 2020 - present"}]

user.colleges           # [
                        #     {
                        #         "name": "Streamer University",
                        #         "date": "2025 - 2026",
                        #         "subject": "Content Creation 101",
                        #         "activities": None,
                        #         "dorm": None,
                        #         "classes": None,
                        #         "desc": None,
                        #     },
                        # ]

user.high_schools       # [{"name": "Streamer High School", "date": "2025 - 2026"}]
user.hobbies            # [{"name": "Gaming", "desc": ""}]

user.interests          # {
                        #     "musics":   [{"name": "Radiohead", "desc": None}],
                        #     "tv_shows": [...],
                        #     "movies":   [...],
                        #     "games":    [...],
                        #     "sports":   [...],
                        # }

user.travels            # [{"name": "Tokyo", "date": "March 2023"}]

user.contacts           # [{
                        #     "socials":         [{"type": "YouTube", "name": "@johndoe"}],
                        #     "phones":          [{"type": "Mobile", "name": "+123456789"}],
                        #     "emails":          [{"type": "Personal", "name": "johndoe@example.com"}],
                        #     "messenger":       [],
                        #     "whatsapp_number": [],
                        #     "media_kit":       [],
                        # }]

user.name_pronunciation # [{"name": "john-Dawg"}]
user.nicknames          # [{"type": "Short", "name": "john"}]

## business
user.business_rating    # "4.6 (100 reviews)"
user.business_address   # "123 Main St, Ohio"
user.business_hours     # "Mon-Fri: 6am-7pm"
```

### Profile methods

```python
# User's posts → Post
for post in user.get_posts():
    print(post.id, post.text)

# User's photos → Photo
for photo in user.get_photos():
    print(photo.id, photo.image_url)

# User's videos/reels → Video
for video in user.get_videos():
    print(video.id, video.url, video.play_count)

# Users following this user → Profile
for follower in user.get_followers():
    print(follower.id, follower.name)

# Users this user follows → Profile
for followee in user.get_followees():
    print(followee.id, followee.name)

# Friends who follow this user → Profile
for friend in user.get_friends_followers():
    print(friend.id, friend.name)

# Friends this user follows → Profile
for friend in user.get_friends_followees():
    print(friend.id, friend.name)
```
---

## Post

```python
post = fgs.Post.from_post_id(ctx, post_id="253053527513133")
# Or from PFBID: post = fgs.Post.from_pfbid(ctx, pfbid="pfbid0qHZRZohg13A1DmZpkFvHr3yuv7y1heFNnNoijtvi5onn1ctx2sjM5rRgTMSh6EGql")
print(post.text)
```

### Post properties

```python
## Identity
post.id                     # "253053527513133"
post.creation_time          # 1690761224
post.url                    # "https://web.facebook.com/Ishowspeed/posts/pfbid..."
post.title                  # None
post.text                   # "Thank you for all the prayers <3"

## Engagement
post.reaction_count         # "47619"
post.share_count            # 2380
post.comments_count         # 1676

post.reactors_visible       # True
post.top_reaction_breakdown # [
                            #     {"id": "1635855486666999", "name": "Haha", "count": 21197},
                            #     {"id": "1678524932434102", "name": "Like", "count": 17562},
                            #     {"id": "867209233497706",  "name": "Love", "count": 6761},
                            #     ...
                            # ]

## Media
post.attachments            # [Photo(id="123", image_url="https://...", url="https://...")]

## Related models
post.owner                  # Profile(id="100044296486382", name="Cristiano Ronaldo", ...)
post.group                  # Group   (the group the post belongs to, if any)
```

### Post methods

```python
# All comments on the post → Comment
for comment in post.get_comments():
    print(comment.id, comment.text)

# Users who reacted to the post → Reactor
for reactor in post.get_reactors():
    print(reactor.reaction_type_id, reactor.profile.name)
```

---

## Comment

A `Comment` may be a top-level comment on a post, or a reply to another comment.

### Comment properties

```python
comment.id                 # "1234567898767876"
comment.text               # "Nice!!"
comment.created_time       # 1790291800
comment.reaction_count     # 12
comment.reply_count        # 3

comment.attachments        # [Photo(id="...", image_url="https://...")]
comment.owner              # Profile(id="...", name="John Doe", ...)
comment.post               # Post(id="1086837787662153", ...)
```

### Comment methods

```python
# Replies to the comment → Comment
for comment_reply in comment.get_replies():
    print(comment_reply.id, comment_reply.text)

    # Sub-replies to the reply (Facebook's max reply depth) → Comment
    for comment_subreply in comment_reply.get_replies():
        print(comment_subreply.id, comment_subreply.text)

# Users who reacted to the comment → Reactor
for reactor in comment.get_reactors():
    print(reactor.reaction_type_id, reactor.profile.name)
```
---

## Group

```python
group = fgs.Group.from_group_id(ctx, group_id="2781022932139267")
# Or from groupname: group = fgs.Group.from_groupname(ctx, groupname="workingmemes")
print(group.name)
```

### Group properties

```python
## Identity
group.id                # "2781022932139267"
group.name              # "Working Memes"
group.url               # "https://www.facebook.com/groups/workingmemes"
group.privacy           # "PUBLIC"
group.member_count      # "1.2M members"
group.profile_picture_url # "https://scontent...jpg"
group.created_time      # 1456789012
group.description       # "Memes for the working class."
group.privacy_info      # "Public group"
group.discoverability_info # "Anyone can find this group"
```

### Group methods

```python
# Group's posts → Post
for post in group.get_posts():
    print(post.id, post.text)

# Group's members → GroupMember
for member in group.get_members():
    print(member.join_status, member.contribution_score, member.profile.name)
```
---

## MarketplaceListing

```python
listing = fgs.MarketplaceListing.from_listing_id(ctx, id="123456789876789")
print(listing.product_details_type)
```
A listing is one of two types, indicated by `product_details_type`:

- **`"FOR_SALE_ITEM"`** — regular Marketplace listing sold by a Facebook user.
- **`"PARTNER_LISTING"`** — partner listing (e.g. eBay).

### MarketplaceListing Properties

```python
## Identity
listing.id              # "123456789876789"
listing.title           # "USB Microphone"
listing.description     # "USB microphone with spit guard..."
listing.url             # "https://web.facebook.com/marketplace/item/123456789876789/"
listing.post_id         # "12345123451234512"
listing.creation_time   # 1790291735                    (FOR_SALE_ITEM only)

## Pricing
listing.currency             # "USD"
listing.price                # 25
listing.strikethrough_price  # 30                       (FOR_SALE_ITEM only)

## Location
listing.location_text   # "Johnstown, PA"
listing.latitude        # 40.322570800781               (FOR_SALE_ITEM only)
listing.longitude       # -78.931274414062              (FOR_SALE_ITEM only)

## Status
listing.is_live         # True                          (FOR_SALE_ITEM only)
listing.is_pending      # False                         (FOR_SALE_ITEM only)
listing.is_sold         # False                         (FOR_SALE_ITEM only)
listing.is_hidden       # False                         (FOR_SALE_ITEM only)

## Product details
listing.product_details_type     # "FOR_SALE_ITEM" or "PARTNER_LISTING"
listing.shipping_cost_text       # None                  (PARTNER_LISTING only)
listing.has_shipping_cost        # None                  (PARTNER_LISTING only)
listing.delivery_window_text     # None                  (PARTNER_LISTING only)
listing.product_details_page_uri # None                  (PARTNER_LISTING only)

## Category / commerce
listing.category_id             # "1234554321123451"
listing.attributes              # [{"name": "Condition", "value": "used_good"}, ...]
listing.delivery_types          # ["IN_PERSON", "PUBLIC_MEETUP"]   (FOR_SALE_ITEM only)
listing.is_shipping_offered     # False
listing.is_purchase_protected   # False                            (FOR_SALE_ITEM only)
listing.inventory_count         # None                             (FOR_SALE_ITEM only)
listing.messaging_enabled       # True                             (FOR_SALE_ITEM only)

## Media
listing.listing_photos          # [
                                #     Photo(id="3477221012465782", image_url="https://...jpg", url=None),
                                #     Photo(id="2159451611596036", image_url="https://...jpg", url=None),
                                # ]

listing.videos                  # [Video(id="...", thumbnail_image_url="https://...", video_url="https://...")]

## Seller (FOR_SALE_ITEM only)
seller = listing.seller

seller.profile.id                      # "123451234512345"
seller.profile.name                    # "OneEvolutionarydawn"
seller.profile.profile_picture_url     # "https://...jpg"
seller.profile.joined_time             # 1615703350
seller.is_verified                     # False
seller.seller_ratings_are_private      # False
seller.seller_ratings_average          # 5.0
seller.seller_ratings_count            # 10
seller.combined_ratings_are_private    # False
seller.combined_ratings_average        # 4.9
seller.combined_ratings_count          # 24

## PartnerSeller (PARTNER_LISTING only)
partner = listing.partner_seller

partner.profile.id                     # "1033819751641974"
partner.profile.name                   # "RICKS HOLLYWOOD"
partner.profile.profile_picture_url    # None
partner.partner_brand_name             # "eBay"
partner.seller_review_count            # 12903
partner.seller_positive_ratings_pct    # 0.994
partner.seller_member_since            # 883251803
partner.number_of_sold_listings        # None
partner.average_ship_time              # None
```

---
## SearchEngine

Facebook search service — profiles, posts, groups, and Marketplace listings.

```python
engine = fgs.SearchEngine(ctx)
```

### Search

Search Facebook for profiles, posts, or groups.

```python
it = engine.search("Ishowspeed", filter_type="profile", exact_match=True)
for item in it:
    print(item.id, item.name)

# filter_type: "all" | "profile" | "post" | "group"
#   "all"      → yields Profile, Post, Group
#   "profile"  → yields Profile
#   "post"     → yields Post
#   "group"    → yields Group
```

### Search marketplace

Search Facebook Marketplace listings.

```python
it = engine.search_marketplace(
    query="iphone",
    is_stock_available=True,
    filter_location_latitude=40.7128,
    filter_location_longitude=-74.0060,
    filter_price_lower_bound=0,
    filter_price_upper_bound=1000,
    filter_radius_km=100,
    item_condition="used_good",        # new | used_like_new | used_good | used_fair
    last_n_days=7,
    sort_by="CREATION_TIME_DESCEND",   # PRICE_DESCEND | PRICE_ASCEND | DISTANCE_ASCEND | CREATION_TIME_DESCEND
)

for listing in it:                     # yields MarketplaceListing
    print(listing.id, listing.title, listing.price)
```

---

## Events (TODO)

- [ ] Add support for scraping Facebook Events

---

## Pagination Iterator

Every iterator-returning method returns a `PaginatedIterator`. Each item
returned by the iterator is a full model object, with all of its properties
and methods available.

For example, `get_followers()` returns full `Profile` objects:

```python
for follower in user.get_followers():
    # Properties: follower.name, follower.gender, follower.is_verified, etc.
    # Methods: follower.get_posts(), follower.get_photos(), etc.

```
###  Pagination — freeze / thaw

The iterator state can be serialized and resumed later:

```python
it = post.get_comments()

# Process the first 10 comments
for i, comment in enumerate(it):
    print(comment.text)
    if i == 9:
        break

# Save state at any point
frozen = it.freeze()
with open("resume.json", "w") as f:
    json.dump(frozen._asdict(), f)

# Later, in a new process, continue where it left off
with open("resume.json") as f:
    frozen = fgs.FrozenPaginatedIterator(**json.load(f))

it2 = post.get_comments()
it2.thaw(frozen)

for comment in it2:
    print(comment.text)
```

---

## Contributing

🤝 Contributions are welcome! Feel free to open an issue or submit a pull request.

