using JSON
using Fire
using Gmsh
using ExtendableGrids
using ExtendableFEM
using StaticArrays: @SArray
using Unitful
using LinearAlgebra
using ZipArchives: ZipWriter, zip_newfile

struct PlateConfig
    id::String
    F::Float64
    E::Float64
    ν::Float64
    radius::Float64
    length::Float64
    element_order::Int64
end

struct Metrics
    max_von_mises_stress_nodes::Float64
end

function value_with_unit(json::JSON.Object{String,Any})
    res = uparse(string(json["value"])*json["unit"])
    return res
end


function parse_config(configfile::String)
    config = JSON.parsefile(configfile)
    id =  config["configuration"]
    F = ustrip(u"Pa",value_with_unit(config["load"]))
    E = ustrip(u"Pa",value_with_unit(config["young-modulus"]))
    ν = config["poisson-ratio"]["value"]
    radius = ustrip(u"m",value_with_unit(config["radius"]))
    length = ustrip(u"m",value_with_unit(config["length"]))
    element_order = config["element-order"]
    return PlateConfig(id,F,E,ν,radius,length,element_order)
end


function plane_stress_elasticity_tensor(E::Float64, ν::Float64)
    G = (1 / (1 + ν)) * E * 0.5
    λ = (ν / (1 - 2ν)) * 2 * G
    return @SArray [
        (λ + 2G) λ 0
        λ (λ + 2G) 0
        0 0 G
    ]
end


function make_kernel(𝐂)
    function LE_kernel_sym!(σ,εv,qpinfo)
        mul!(σ,𝐂,εv)
    end 
    return LE_kernel_sym!
end

function u_ex_kernel!(result,qpinfo)
    x = qpinfo.x[1]
    y = qpinfo.x[2]
    a = qpinfo.params[1]
    T = qpinfo.params[2]
    E = qpinfo.params[3]
    ν = qpinfo.params[4]
    r = sqrt(x^2+y^2)
    θ = atan(y,x)
    k = (3.0-ν)/(1.0+ν)
    Ta_8mu = T*a*(1.0+ν)/(4.0*E)
    ct = cos(θ)
    c3t = cos(3.0*θ)
    st = sin(θ)
    s3t = sin(3.0*θ)
    fac = 2.0 * (a/r)^3


    result[1] = Ta_8mu * (
          (r/a) * (k + 1.0) * ct
        + 2.0*(a/r)*((1.0 + k) * ct + c3t)
        - fac * c3t
    )
    result[2] = Ta_8mu * (
          (r/a) * (k - 3.0) * st
        + 2.0*(a/r)*((1.0 - k) * st + s3t)
        - fac * s3t
    )
end

function exact_error!(result,u, qpinfo)
    u_ex_kernel!(result,qpinfo)
    result .-= u 
    result .= result .^2
    return nothing
end

function solve_plate_with_hole(config::PlateConfig,grid::ExtendableGrid,outputzip::String,outputmetrics::String)

    bfacemask!(grid,[0.,0.],[config.radius,config.radius],50)

    PD = ProblemDescription("Linear elastic 2D Plate with hole, configuration "*config.id)
    u = Unknown("u"; name= "displacement")
    assign_unknown!(PD, u)
    𝐂 = plane_stress_elasticity_tensor(config.E,config.ν)
    LE_kernel_sym! = make_kernel(𝐂)
    assign_operator!(PD, BilinearOperator(LE_kernel_sym!, [εV(u,1.0)]))
    assign_operator!(PD, InterpolateBoundaryData(u, u_ex_kernel!; regions = [3,4], params = [config.radius,config.F,config.E,config.ν]))
    assign_operator!(PD, HomogeneousBoundaryData(u; regions = [1], mask = [1,0]))
    assign_operator!(PD, HomogeneousBoundaryData(u; regions = [2], mask = [0,1]))

    FEType = H1Pk{2,2, config.element_order}
    FES = FESpace{FEType}(grid)
    sol = solve(PD,FES; timeroutputs = :hide)

    u_ex = FEVector(FES; name="exact solution")
    interpolate!(u_ex.FEVectorBlocks[1],ON_CELLS,u_ex_kernel!;params = [config.radius,config.F,config.E,config.ν])
    u_exx = nodevalues(u_ex.FEVectorBlocks[1])[1,:]
    u_exy = nodevalues(u_ex.FEVectorBlocks[1])[2,:]

    u_x = nodevalues(sol[u])[1,:]
    u_y = nodevalues(sol[u])[2,:]
    u_mag = sqrt.(u_x.*u_x.+u_y.*u_y)
    uex_mag = sqrt.(u_exx.*u_exx.+u_exy.*u_exy)

    # TODO: Stress calculations

    metrics = Metrics(0.)
    # TODO: L2 error, see Example301
    ErrorIntegrationExact = ItemIntegrator(exact_error!, [id(u)]; quadorder = 8,params = [config.radius,config.F,config.E,config.ν])

    error = evaluate(ErrorIntegrationExact, sol)

    L2error = sqrt(sum(error))

    outputvtk = splitdir(outputzip)[1]*"/results_"*config.id*".vtu";
    writeVTK(outputvtk,grid;compress=false, u_x=u_x,u_y=u_y,u_mag=u_mag,uexx=u_exx,uexy=u_exy,uex=uex_mag)
    f = open(outputvtk,"r")
    vtkcontent = read(f,String)
    ZipWriter(outputzip) do w
        zip_newfile(w, "result_"*config.id*".vtu";compress=true)
        write(w,vtkcontent)
    end
    JSON.json(outputmetrics,metrics;pretty=true)

end

"run linear elastic plate with a hole using ExtendableFEM.jl"
Fire.@main function run_simulation(;
    configfile::String="", 
    meshfile::String="",
    outputzip::String="",
    outputmetrics::String=""
)
    if(isempty(configfile))
        @error "No configuration file given"
    end
    config = parse_config(configfile)
    if(isempty(meshfile))
        @error "No mesh file given"
    end
    if(isempty(outputzip))
        @error "No output zip file given"
    end
    if(isempty(outputmetrics))
        @error "No output metrics file given"
    end
    grid = simplexgrid_from_gmsh(meshfile)
    solve_plate_with_hole(config,grid,outputzip,outputmetrics)

    return
end