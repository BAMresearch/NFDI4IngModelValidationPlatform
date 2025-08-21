from __future__ import print_function, absolute_import, division  # makes KratosMultiphysics backward compatible with python 2.6 and 2.7
import json
import sys
from argparse import ArgumentParser

import gmsh
import meshio
import re
from pint import UnitRegistry
import numpy as np
import os

ureg = UnitRegistry()

import KratosMultiphysics
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import sys

import pyvista
from pathlib import Path


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Run FEniCS simulation for a plate with a hole.\n"
        "Inputs: --input_parameter_file, --input_kratos_inputfile, --input_kratos_materialfile\n"
        "Outputs: --output_solution_file_zip, --output_metrics_file"
    )
    parser.add_argument(
        "--input_parameter_file",
        required=True,
        help="JSON file containing simulation parameters (input)",
    )
    parser.add_argument(
        "--input_kratos_inputfile",
        required=True,
        help="Path to the kratos input file (input)",
    )
    parser.add_argument(
        "--input_kratos_materialfile",
        required=True,
        help="Path to the kratos material file (input)",
    )
    args, _ = parser.parse_known_args()

    with open(args.input_kratos_inputfile, "r") as kratos_input:
        parameters = KratosMultiphysics.Parameters(kratos_input.read())

    model = KratosMultiphysics.Model()
    simulation = StructuralMechanicsAnalysis(model, parameters)
    simulation.Run()