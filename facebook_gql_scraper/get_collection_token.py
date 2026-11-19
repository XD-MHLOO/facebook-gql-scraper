import json

PREFIX = "for (;;);"

def get_collection_token(raw: str) -> str | None:
    text = raw
    if text.startswith(PREFIX):
        text = text[len(PREFIX):]
    data = json.loads(text)
        
    result = data["payload"]["payload"]["result"]
    if result["type"] == "route_definition":
        return result["exports"]["rootView"]["props"]["collectionToken"]
    if result["type"] == "route_redirect":
        return result["redirect_result"]["exports"]["rootView"]["props"]["collectionToken"]
    return None