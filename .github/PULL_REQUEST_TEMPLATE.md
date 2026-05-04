## Summary

- Describe the user-visible change.
- Link the issue or explain the motivation.

## Validation

- [ ] `python -m pytest`
- [ ] `python scripts/check_docs.py`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`
- [ ] Updated user-facing docs if needed

## Checklist

- [ ] Stable vs experimental behavior is still correct
- [ ] New or changed CLI/tool behavior is documented
- [ ] No secrets or private host details were added
