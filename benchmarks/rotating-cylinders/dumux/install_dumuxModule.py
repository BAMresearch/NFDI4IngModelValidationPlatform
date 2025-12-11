#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil

top = "."
os.makedirs(top, exist_ok=True)


def runFromSubFolder(cmd, subFolder):
    folder = os.path.join(top, subFolder)
    try:
        subprocess.run(cmd, cwd=folder, check=True)
    except Exception as e:
        cmdString = ' '.join(cmd)
        sys.exit(
            "Error when calling:\n{}\n-> folder: {}\n-> error: {}"
            .format(cmdString, folder, str(e))
        )


def installModule(subFolder, url, branch, revision):
    if not os.path.exists(subFolder):
        runFromSubFolder(['git', 'clone', url, subFolder], '.')
        if branch:
            runFromSubFolder(['git', 'checkout', branch], subFolder)
        if revision:
            runFromSubFolder(['git', 'reset', '--hard', revision], subFolder)
    else:
        print(f"Skip cloning {url} since target '{subFolder}' already exists.")


def installLocalModule(subFolder, localPath):
    """Copy dumuxModule from local build context instead of cloning from GitHub."""
    target = os.path.join(top, subFolder)

    if os.path.exists(target):
        print(f"Skip copying local module '{subFolder}' — target already exists.")
        return

    if not os.path.exists(localPath):
        sys.exit(f"Local dumuxModule path not found: {localPath}")

    print(f"Copying local module '{localPath}' → '{target}'")
    shutil.copytree(localPath, target)


def applyPatch(subFolder, patch):
    sfPath = os.path.join(top, subFolder)
    patchPath = os.path.join(sfPath, 'tmp.patch')
    with open(patchPath, 'w') as patchFile:
        patchFile.write(patch)
    runFromSubFolder(['git', 'apply', 'tmp.patch'], subFolder)
    os.remove(patchPath)


print("Installing dune-istl")
installModule("dune-istl",
              "https://gitlab.dune-project.org/core/dune-istl.git",
              "origin/releases/2.10",
              "21c67275b17e93918365177f93f42e4aaa9afd23")

print("Installing dune-grid")
installModule("dune-grid",
              "https://gitlab.dune-project.org/core/dune-grid.git",
              "origin/releases/2.10",
              "954436b88247e904628ec4d7c8bb7b2eaac08900")

print("Installing dune-localfunctions")
installModule("dune-localfunctions",
              "https://gitlab.dune-project.org/core/dune-localfunctions.git",
              "origin/releases/2.10",
              "ddbf693b5f9c867b2d58d418fe130bbe92c06a99")

print("Installing dune-geometry")
installModule("dune-geometry",
              "https://gitlab.dune-project.org/core/dune-geometry.git",
              "origin/releases/2.10",
              "5673e95ac364ad3498aed9eaf65e0d224384d15a")

print("Installing dune-uggrid")
installModule("dune-uggrid",
              "https://gitlab.dune-project.org/staging/dune-uggrid.git",
              "origin/releases/2.10",
              "cf2513efb6497dc95744649e0658cedef2980bff")

print("Installing dune-common")
installModule("dune-common",
              "https://gitlab.dune-project.org/core/dune-common.git",
              "origin/releases/2.10",
              "fa09b5bd31efa38cc051e22717b0d259de5ae8a1")

print("Installing dumux")
installModule("dumux",
              "https://git.iws.uni-stuttgart.de/dumux-repositories/dumux.git",
              "origin/releases/3.9",
              "bb99f6bb0d6db317aae6da4000ecd37ccc664187")

print("Configuring project")
runFromSubFolder(
    ['./dune-common/bin/dunecontrol', '--opts=dumuxmodule/cmake.opts', 'all'],
    '.'
)
