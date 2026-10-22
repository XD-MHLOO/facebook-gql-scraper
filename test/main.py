import facebook_gql_scraper as fgs

ctx = fgs.FacebookContext(cookies_file="facebook_cookies.json")
user = fgs.Profile.from_user_id(ctx, id="100084254631043")
# Or from username: user = fgs.Profile.from_username(ctx, username="Ishowspeed")
print(user.name)