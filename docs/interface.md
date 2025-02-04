# Generalized interface for constitutive models

Abaqus UMAT header:

```Fortran
SUBROUTINE UMAT(STRESS,STATEV,DDSDDE,SSE,SPD,SCD,
     1 RPL,DDSDDT,DRPLDE,DRPLDT,
     2 STRAN,DSTRAN,TIME,DTIME,TEMP,DTEMP,PREDEF,DPRED,CMNAME,
     3 NDI,NSHR,NTENS,NSTATV,PROPS,NPROPS,COORDS,DROT,PNEWDT,
     4 CELENT,DFGRD0,DFGRD1,NOEL,NPT,LAYER,KSPT,KSTEP,KINC)
```

Ansys usermat header

```Fortran
subroutine usermat(
     &                   matId, elemId,kDomIntPt, kLayer, kSectPt,
     &                   ldstep,isubst,keycut,
     &                   nDirect,nShear,ncomp,nStatev,nProp,
     &                   Time,dTime,Temp,dTemp,
     &                   stress,ustatev,dsdePl,sedEl,sedPl,epseq,
     &                   Strain,dStrain, epsPl, prop, coords, 
     &                   var0, defGrad_t, defGrad,
     &                   tsstif, epsZZ,
     &                   var1, var2, var3, var4, var5,
     &                   var6, var7, var8)
```


The following table shows the correspondence between the variables in the two interfaces:
**Warning: Table generated by github copilot. Check later!!**

| Abaqus | Ansys | Description |
|--------|-------|-------------|
| STRESS | stress | Stress tensor |
| STATEV | ustatev | State variables |
| DDSDDE | dsdePl | Material tangent stiffness |
| SSE | sedEl | Elastic strain energy density |
| SPD | sedPl | Plastic strain energy density |
| SCD | epseq | Equivalent plastic strain |
| RPL | epsPl | Equivalent plastic strain rate |
| DDSDDT | tsstif | Tangent stiffness for thermal strain |
| DRPLDE | | Derivative of equivalent plastic strain rate with respect to strain |
| DRPLDT | | Derivative of equivalent plastic strain rate with respect to temperature |
| STRAN | Strain | Total strain tensor |
| DSTRAN | dStrain | Incremental strain tensor |
| TIME | Time | Current time |
| DTIME | dTime | Time increment |
| TEMP | Temp | Current temperature |
| DTEMP | dTemp | Temperature increment |
| PREDEF | | Predefined field variable |
| DPRED | | Predefined field variable increment |
| CMNAME | | Material name |
| NDI | nDirect | Number of direct stress components |
| NSHR | nShear | Number of shear stress components |
| NTENS | ncomp | Number of stress components |
| NSTATV | nStatev | Number of state variables |
| PROPS | prop | Material properties |
| NPROPS | nProp | Number of material properties |
| COORDS | coords | Element coordinates |
| DROT | | Rotation matrix |
| PNEWDT | | Suggested time increment |
| CELENT | | Element characteristic length |
| DFGRD0 | defGrad_t | Deformation gradient at the beginning of the time step |
| DFGRD1 | defGrad | Deformation gradient at the end of the time step |
| NOEL | elemId | Element number |
| NPT | kDomIntPt | Integration point number |
| LAYER | kLayer | Layer number |
| KSPT | kSectPt | Section point number |
| KSTEP | ldstep | Load step number |
| KINC | | Increment number |
|  | var0 | User-defined variable |
|  | var1 | User-defined variable |
|  | var2 | User-defined variable |
|  | var3 | User-defined variable |
|  | var4 | User-defined variable |
|  | var5 | User-defined variable |
|  | var6 | User-defined variable |
|  | var7 | User-defined variable |
|  | var8 | User-defined variable |

## Possible problems

### Rotations

The Abaqus interface contains a rotation matrix `DROT` which is not present in the Ansys interface. It should however be possible to calculate the rotation matrix from the deformation gradient tensors `DFGRD0` and `DFGRD1` which are present in both interfaces. However, only the Green-Naghdi stress rate can determined that way. The Jaumann rate requires the spin tensor $\mathbf W$.

### Multiple constitutive models

In Abaqus, it is recommended to achieve multiple constitutive laws through the `CMNAME` variable which is used to call a different subroutine depending on the value of `CMNAME`. Since Ansys does not have this parameter, it is necessary to use a different approach to achieve the same functionality.

### Order of Voigt notation

Abaqus implicit uses the order $[\sigma_{11}, \sigma_{22}, \sigma_{33}, \sigma_{12},\sigma_{13},\sigma_{23}]$, whereas Ansys and Abaqus explicit use the order $[\sigma_{11}, \sigma_{22}, \sigma_{33}, \sigma_{13},\sigma_{23},\sigma_{12}]$. This means that the stress, strain and tangent must be reordered when passing them between the two interfaces.

## Interface in Rust (WIP)

The following is a preliminary suggestion for an interface that covers the most important use cases of the Abaqus and Ansys interfaces. The interface is written in Rust with C types such that interoperability between different languages is possible.

```rust
fn umat(
    strain: &[f64],
    del_strain: &[f64],
    def_grad_0: &[f64],
    def_grad_1: &[f64],
    properties: &[f64],
    stress: &mut [f64],
    state_vars: &mut [f64],
    tangent: &mut [f64],
    time: f64,
    del_time: f64,
    n_properties: usize,
    n_state_vars: usize,
    n_stress_strain: usize,
) {
    // implementation
}
```

This interface needs to be converted to a C-compatible interface for use in Abaqus and Ansys. The following code shows how this can be done using c types in Rust.

```rust

use core::ffi::{c_double, c_int, c_char};

#[no_mangle]
pub extern "C" fn umat(
    strain: *const c_double,
    del_strain: *const c_double,
    def_grad_0: *const c_double,
    def_grad_1: *const c_double,
    properties: *const c_double,
    stress: *mut c_double,
    state_vars: *mut c_double,
    tangent: *mut c_double,
    time: c_double,
    del_time: c_double,
    n_properties: c_int,
    n_state_vars: c_int,
    n_stress_strain: c_int,
) {
    // implementation
}
```

In order to convert between interfaces, one could write $2^n$ conversion wrappers ($n$ the number of coverred Interfaces) or alternatively, all conversions go through the generalized interface. This would be easiest to implement, but could potentially be slower due to several conversions in the stresses, tangents, etc. However, using macros and const functionalities to generate conversion tables, factors, and so on, could potentially make this more efficient.