# `Pypi-server` Release Workflow Reference

The official `pypi-server` releases are handled using
[GitHub Actions workflows](../../../.github/workflows/).

## General release process

```mermaid
flowchart LR
    rc["release-candidate ⭐️"]
    rn["release-notes 📝"]
    rm["confirmed-tag ✅"]
    ci["code-checks 🧪"]
    pk["build-and-pack 📦"]
    py["pypi-index 🗃️"]
    do["docker-hub 🐳"]
    gh["gh-container-registry 🚀"]
    gr["github-release 📣"]

    subgraph "Preparation 🌱"
    rc-->rn-->rm
    end
    subgraph "Integration 🪴"
    rm-->ci-->pk
    end
    subgraph "Deploy 🌳"
    pk--> py & do & gh & gr
    end
```

## Process walkthrough

> 🗺️ _**This description approximates the real GitHub workflows and steps.**_  
> 👀 _For a more detailed view, do check out the linked resources as you read._

### Preparation 🌱

> 🛠️ _These step are applicable only for maintainers._

#### Release candidate ⭐️

A new release candidate can be initiated _**manually** or **on a monthly schedule**_.

This is done via the [`rc.yml`](../../../.github/workflows/rc.yml) GH
Workflow's `workflow_dispatch` or `schedule` trigger.

The workflow automatically prepares a list of changes for the `CHANGES.rst` and
creates a new Pull Request _(rc PR)_ named
`chore(auto-release-candidate-YYY-MM-DD)` including these draft change notes.

#### Release notes 📝

In the created rc PR, open the `CHANGES.rst` and:

1. _**adjust the suggested changelog items**_
2. _**choose & set the next released version**_
3. _**set the right release date**_

Commit the changes and push them to the head branch of the rc PR.

#### Confirmed tag ✅

1. Once everything is looking good, _**approve and merge**_ the rc PR.

    It will create the new _commit_ with the updated `CHANGES.rst`
    on the default branch.

2. Next, to create a release tag, _**manually run**_ the
    [`rt.yml`](../../../.github/workflows/rt.yml) GH Workflow.

    First, it executes all the [`bumpver`](../../../bin/README.md) procedures.

    Next, it commits and pushes the new **version tag** to the default branch.

### Integration 🪴

#### Code checks 🧪

Once any _commmit_ or _tag_ is pushed to the default branch,
[`ci.yml`](../../../.github/workflows/ci.yml) GH Workflow automatically
executes diverse code checks: e.g. _linting_, _formatting_, _tests_.

#### Build and pack 📦

If all the checks are successful, [`ci.yml`](../../../.github/workflows/ci.yml)
builds all the code artifacts: e.g. _wheels_, _docker images_.

### Deploy 🌳

#### Publish to PyPi 🗃️

> 🏷️ This happens only on new _version tags_.

Once everythig is built, [`ci.yml`](../../../.github/workflows/ci.yml) uploads
the wheels to the [`pypiserver` PyPi project](https://pypi.org/project/pypiserver/).

#### Publish to Docker Hub 🐳

> 🏷️ Docker image _tags_ are determined on the fly.

If all is successful so far, [`ci.yml`](../../../.github/workflows/ci.yml) tags
the built docker images and pushes them to the
[`pypiserver` Docker Hub repository](https://hub.docker.com/r/pypiserver/pypiserver).

#### Publish to GitHub Container Registry 🚀

> 🏷️ Docker image _tags_ are determined on the fly.

For all `stable` (i.e. `latest`, tag, release ...) tags derived by
[`ci.yml`](../../../.github/workflows/ci.yml) tags,
the built docker images are _also_ pushed to
[`pypiserver` GitHub Container Registry](https://github.com/orgs/pypiserver/packages?repo_name=pypiserver).

#### Publish a GitHub Release draft 📣

> 🛠️ _This step is applicable only for maintainers._  
> 🏷️ This happens only on new _version tags_.  

To make the release noticeable, [`ci.yml`](../../../.github/workflows/ci.yml)
also creates a _draft_
[GitHub Release entry in the `pypiserver` repository](https://github.com/pypiserver/pypiserver/releases).

> 📝 Since it is a _draft_, the entry should be _manually_ adjusted further.
