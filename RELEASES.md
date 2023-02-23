# Release process

Only tags are used by now (not releases).

# Tagging a release

If a version needs to be changed, edit `construct-gallery/__version__.py`.

This file is read by *setup.py*.

If the version is not changed, the publishing procedure works using the same version with a different build number.

The GITHUB_RUN_NUMBER environment variable, when available, is read by *setup.py*.

Push all changes:

```shell
git commit -a
git push
```

_After pushing the last commit_, add a local tag (shall be added AFTER the commit that needs to be published):

```shell
git tag # list local tags
git tag v1.0.0
```

Notes:

- correspondence between tag and `__version__.py` is not automatic.
- the tag must start with "v" if a GitHub Action workflow needs to be run

Push this tag to the origin, which starts the PyPI publishing workflow (GitHub Action):

```shell
git push origin v1.0.0
git ls-remote --tags https://github.com/Ircama/construct-gallery # list remote tags
```

Check the published tag here: https://github.com/Ircama/construct-gallery/tags

It shall be even with the last commit.

Check the GitHub Action: https://github.com/Ircama/construct-gallery/actions

Check PyPI:

- https://test.pypi.org/manage/project/construct-gallery/releases/
- https://pypi.org/manage/project/construct-gallery/releases/

End user publishing page:

- https://test.pypi.org/project/construct-gallery/
- https://pypi.org/project/construct-gallery/

Verify whether wrong builds need to be removed.

Test installation:

```shell
cd
python3 -m pip uninstall -y construct-gallery
python3 -m pip install construct-gallery
python3
import wx  # (not needed for strict testing)
from construct_gallery import ConstructGallery, GalleryItem
from bleak_scanner_construct import BleakScannerConstruct
from collections import OrderedDict  # (not needed for strict testing)
from bleak import BleakScanner  # pip3 install bleak (not needed for strict testing)
quit()
python3 -m pip uninstall -y construct-gallery
```

# Updating the same tag (using a different build number for publishing)

```shell
git tag # list tags
git tag -d v1.0.0 # remove local tag
git push --delete origin v1.0.0 # remove remote tag
git ls-remote --tags https://github.com/Ircama/construct-gallery # list remote tags
```

Then follow the tagging procedure again to add the tag to the latest commit.

# Testing the build procedure locally

```shell
cd <repository directory>
```

## Local build (using build):

Prerequisite:

```shell
pip3 install build
```

Command:

```shell
python3 -m build --sdist --wheel --outdir dist/ .
python3 -m twine upload --repository testpypi dist/*
```

## Local build (using setup):

```shell
python3 setup.py sdist bdist_wheel
python3 -m twine upload --repository testpypi dist/*
```

## Local build (using build versions):

```shell
GITHUB_RUN_NUMBER=31 python3 setup.py sdist bdist_wheel
python3 -m twine upload --repository testpypi dist/*
```

## Removing directories

```shell
ls -l dist
rm -r build dist construct-gallery.egg-info
```

# Check version data

- https://pypi.org/pypi/construct-gallery/json
- https://test.pypi.org/pypi/construct-gallery/json
