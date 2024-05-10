# Build scripts folder

## Highlight files

- `bumpver.py` : Bump, commit and tag new project versions
- `package.sh` : Build deployable artifact (wheel) in `/dist/` folder.

## Fully manual release check-list

1. Update `/CHANGES.rst` (+ Title + Date).

2. Push to GitHub to run all TCs once more.

3. Bump version: commit & tag it with `/bin/bumpver.py`. Use `--help`.
   > 💡 Read [PEP-440](https://www.python.org/dev/peps/pep-0440/) to decide the version.

4. Push it in GitHub with `--follow-tags`.

### Manually publishing a new package

1. Generate package *wheel* with `/bin/package.sh`.

2. Upload to PyPi with `twine upload -s -i <gpg-user> dist/*`

3. Ensure that the new tag is built on
   [`hub.docker.com`](https://hub.docker.com/r/pypiserver/pypiserver)
   as `latest` and as a direct tag reference.

4. Copy release notes from `/CHANGES.rst` in GitHub as new *"release"*
   page on the new tag.
   > 💡 Check syntactic differences between `.md` and `.rst` files.
