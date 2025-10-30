# Parameter JSON File

## Overview

These `parameter_*.json` files define all the necessary parameters for mesh generation, material properties, boundary conditions, and solver settings for finite element simulations. Each parameter file represents a unique configuration that will be processed by the workflow system.

## Parameter File Format
Given below is an example of the file `parameters_1.json` from the `linear-elastic-plate-with-hole`example.

<!-- ### Example: `parameters_1.json`-->

```json
{
    "configuration": "1",    
    "radius": {
        "value": 0.33,
        "unit": "m"
    },
    "length": {
        "value": 1.0,
        "unit": "m"
    },
    "load": {
        "value": 100.0,
        "unit": "MPa"
    },
    "element-size": {
        "value": 0.1,
        "unit": "m"
    },
    "element-order": 1,
    "element-degree": 1,
    "quadrature-rule": "gauss",
    "quadrature-degree": 1,
    "young-modulus": {
        "value": 210e9,
        "unit": "Pa"
    },
    "poisson-ratio": {
        "value": 0.3,
        "unit": ""
    }
}
```

## Descriptions

### Configuration Identifier

| Parameter | Type | Description |
|-----------|------|-------------|
| `configuration` | string | Unique identifier for this parameter set. Used in output file naming and workflow tracking. Must be unique across all parameter files. |


### Geometry Parameters

| Parameter | Value Type | Unit | Description |
|-----------|------------|------|-------------|
| `radius` | float | m | Radius of the circular hole in the plate. |
| `length` | float | m | Characteristic length of the plate domain. |


### Loading Conditions

| Parameter | Value Type | Unit | Description |
|-----------|------------|------|-------------|
| `load` | float | MPa | Applied stress/pressure boundary condition. |


### Mesh Parameters

| Parameter | Value Type | Unit | Description |
|-----------|------------|------|-------------|
| `element-size` | float | m | Characteristic element size for mesh generation. Controls mesh density. |
| `element-order` | integer | - | Order of finite element shape functions (1 = linear, 2 = quadratic). |
| `element-degree` | integer | - | Polynomial degree of the finite element basis functions. |


### Numerical Integration Parameters

| Parameter | Value Type | Unit | Description |
|-----------|------------|------|-------------|
| `quadrature-rule` | string | - | Type of numerical integration scheme used in finite element calculations. |
| `quadrature-degree` | integer | - | Degree of accuracy for the quadrature rule. Must be sufficient for the element degree. |


### Material Properties

| Parameter | Value Type | Unit | Description |
|-----------|------------|------|-------------|
| `young-modulus` | float | Pa | Defines material stiffness. |
| `poisson-ratio` | float | - | Defines the ratio of lateral to axial strain. |

