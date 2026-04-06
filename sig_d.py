import inspect
import browser_use
import json
with open("sig.json", "w") as f:
    json.dump([p for p in inspect.signature(browser_use.Browser.__init__).parameters], f)
