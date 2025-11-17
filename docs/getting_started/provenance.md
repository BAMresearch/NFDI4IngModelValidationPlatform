# Provenance

The package stores the provenance records i.e.:

- which input files were used,
- which processes or scripts were executed,
- what parameters, software versions, and container images were used,
- what outputs each step produced, etc.

While using nextflow, provenance reports of the workflow executions are rendered using [nf-prov](https://github.com/nextflow-io/nf-prov) plugin. In the case of snakemake, [Metadata4ing reporter](https://github.com/izus-fokus/snakemake-report-plugin-metadata4ing) is used. The provenance report is stored in [RO-Crate](https://www.researchobject.org/ro-crate/) format.

## Terminologies

### Parameter Extractor

`parameter_extractor.py` passes arguments to the metadata4ing reporter plugin. It parses the parameter configuration files and their corresponding output files.

### Metrics Plotting

`plot_metrics.py`contains implementation for:

- Reading the RO-Crate files using [rdflib](https://github.com/RDFLib/rdflib).
- Running a SPARQL query on the rdflib graph objects.
- Plotting the simulation outputs tool-wise from different parameter configuration runs.