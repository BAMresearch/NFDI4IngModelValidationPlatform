This file has been created automatically. Please adapt it to your needs.

## Content

The content of this DUNE module was extracted from the module `dumux`.
In particular, the following subFolder of `dumux` have been extracted:
*   `test/freeflow/navierstokes/rotatingcylinders`


Additionally, all headers in `dumux` that are required to build the
executables from the sources
*   `test/freeflow/navierstokes/rotatingcylinders/main.cc`


have been extracted. You can configure the module just like any other DUNE
module by using `dunecontrol`. For building and running the executables,
please go to the build folders corresponding to the sources listed above.


## License

This project is licensed under the terms and conditions of the GNU General Public
License (GPL) version 3 or - at your option - any later version.
The GPL can be found under [GPL-3.0-or-later.txt](LICENSES/GPL-3.0-or-later.txt)
provided in the `LICENSES` directory located at the topmost of the source code tree.


## Version Information

|      module name      |      branch name       |                 commit sha                 |         commit date         |
|-----------------------|------------------------|--------------------------------------------|-----------------------------|
|       dune-istl       |  origin/releases/2.10  |  21c67275b17e93918365177f93f42e4aaa9afd23  |  2025-02-03 09:13:05 +0000  |
|       dune-grid       |  origin/releases/2.10  |  954436b88247e904628ec4d7c8bb7b2eaac08900  |  2024-10-22 15:31:40 +0000  |
|  dune-localfunctions  |  origin/releases/2.10  |  ddbf693b5f9c867b2d58d418fe130bbe92c06a99  |  2025-06-27 05:40:52 +0000  |
|     dune-geometry     |  origin/releases/2.10  |  5673e95ac364ad3498aed9eaf65e0d224384d15a  |  2024-09-04 16:39:39 +0200  |
|      dune-uggrid      |  origin/releases/2.10  |  cf2513efb6497dc95744649e0658cedef2980bff  |  2024-09-05 08:40:59 +0200  |
|      dune-common      |  origin/releases/2.10  |  fa09b5bd31efa38cc051e22717b0d259de5ae8a1  |  2025-06-03 21:04:17 +0000  |

## Installation

The installation procedure is done as follows:
Create a root folder, e.g. `DUMUX`, enter the previously created folder,
clone this repository and use the install script `install_dumuxModule.py`
provided in this repository to install all dependent modules.

```sh
mkdir DUMUX
cd DUMUX
git clone git@github.com:Sarbani-Roy/benchmark.git dumuxModule
./dumuxModule/install_dumuxModule.py
```

This will clone all modules into the directory `DUMUX`,
configure your module with `dunecontrol` and build tests.

