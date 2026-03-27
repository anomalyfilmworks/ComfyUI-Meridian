import os
import server
from aiohttp import web
from .meridian import Meridian, NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web/js"

__all__ = ["Meridian", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

__version__ = "2.0.0"


@server.PromptServer.instance.routes.get("/meridian/getpath")
async def get_path(request):
    query = request.rel_url.query
    if "path" not in query:
        return web.Response(status=204)

    path = os.path.abspath(query["path"].strip().strip('"').strip("'"))

    if not os.path.exists(path):
        return web.json_response([])

    valid_items = []
    for item in os.scandir(path):
        try:
            if item.is_dir():
                valid_items.append(item.name + "/")
        except OSError:
            pass

    valid_items.sort()
    return web.json_response(valid_items)


@server.PromptServer.instance.routes.get("/meridian/scandir")
async def scan_dir(request):
    query = request.rel_url.query
    if "path" not in query:
        return web.Response(status=204)

    path = os.path.abspath(query["path"].strip().strip('"').strip("'"))

    if not os.path.isdir(path):
        return web.json_response({"error": "Invalid path"})

    valid_exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}
    try:
        frame_count = sum(
            1 for f in os.listdir(path)
            if os.path.splitext(f)[1].lower() in valid_exts
        )
    except Exception:
        return web.json_response({"error": "Could not read directory"})

    return web.json_response({"frame_count": frame_count})
