import json
import traceback

try:
    import browser_use
    fields = []
    if hasattr(browser_use, 'BrowserConfig'):
        fields = dir(browser_use.BrowserConfig)
    else:
        fields = dir(browser_use.browser)
    with open("fields.json", "w") as f:
        json.dump(fields, f)
except Exception as e:
    with open("fields.json", "w") as f:
        f.write(traceback.format_exc())