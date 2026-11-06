# Integration examples

Start with [the app wrapper](../../docs/wrap-your-app.md) for an existing executable.
The examples here cover deeper API integration.

See [the integration guide](../../docs/integration-guide.md) for the stable API,
security boundaries and which files need adaptation.

With the library installed:

```sh
python3 examples/integration/startup.py
iphone-connectivity-demo check --json | python3 examples/integration/consume-json.py
```

`request-repair.py` is intended for a user-triggered application action. It may
open a PolicyKit administrator prompt. It is not an installation hook.
