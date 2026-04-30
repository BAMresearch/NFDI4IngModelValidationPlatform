from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

M4I = Namespace("http://w3id.org/nfdi4ing/metadata4ing#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
CR = Namespace("http://mlcommons.org/croissant/")

HAS_NUMERICAL_VALUE = M4I.hasNumericalValue
HAS_STRING_VALUE = M4I.hasStringValue
HAS_UNIT = M4I.hasUnit
HAS_KIND_OF_QTY = M4I.hasKindOfQuantity
HAS_PART = OBO.BFO_0000051
HAS_INPUT = OBO.RO_0002233
HAS_OUTPUT = OBO.RO_0002234
USES_CONFIG = M4I.usesConfiguration
HAS_EMPLOYED_TOOL = M4I.hasEmployedTool
DATA_TYPE = M4I.dataType
JSON_PATH = CR.jsonPath
INVESTIGATES = M4I.investigates
EVALUATES = M4I.evaluates
USES = URIRef("https://mardi4nfdi.de/mathmoddb#uses")
DESCRIBED_BY = URIRef("https://mardi4nfdi.de/mathmoddb#describedAsDocumentedBy")
REPRESENTS = URIRef("http://semanticscience.org/resource/SIO_000210")
HAS_SOURCE = CR.source
HAS_EXTRACT = CR.extract
# Current benchmark.json maps "file object" to this predicate IRI.
HAS_FILE_OBJECT = URIRef("http://mlcommons.org/croissant/FileObject")
HAS_FILE_OBJECT_ALT = URIRef("http://mlcommons.org/croissant/fileObject")

T_BENCHMARK = M4I.Benchmark
T_NUMERICAL_VARIABLE = M4I.NumericalVariable
T_PROCESSING_STEP = M4I.ProcessingStep
T_FIELD = CR.Field


@dataclass
class KGNode:
    id: str
    label: Optional[str] = None


@dataclass
class ResearchProblem(KGNode):
    pass


@dataclass
class MathematicalModel(KGNode):
    pass


@dataclass
class Publication(KGNode):
    pass


@dataclass
class NumericalVariable(KGNode):
    unit: Optional[str] = None
    quantity_kind: Optional[str] = None
    field_mapping: Optional["FieldMapping"] = None


@dataclass
class NumericalParameter(KGNode):
    numerical_value: Optional[float] = None
    unit: Optional[str] = None
    field_mapping: Optional["FieldMapping"] = None


@dataclass
class TextParameter(KGNode):
    string_value: Optional[str] = None
    unit: Optional[str] = None
    field_mapping: Optional["FieldMapping"] = None


@dataclass
class FieldMapping:
    field_id: str
    data_type: Optional[str] = None
    source_id: Optional[str] = None
    extract_id: Optional[str] = None
    json_path: Optional[str] = None
    file_object_id: Optional[str] = None
    file_object_label: Optional[str] = None


ParameterEntry = Union[NumericalParameter, TextParameter, NumericalVariable]


@dataclass
class ParameterSet(KGNode):
    identifier: Optional[str] = None
    parts: list[ParameterEntry] = field(default_factory=list)


@dataclass
class Tool(KGNode):
    pass


@dataclass
class IOObject(KGNode):
    pass


@dataclass
class ProcessingStep(KGNode):
    inputs: list[IOObject] = field(default_factory=list)
    outputs: list[IOObject] = field(default_factory=list)
    configurations: list[ParameterSet] = field(default_factory=list)
    employed_tools: list[Tool] = field(default_factory=list)


@dataclass
class SemanticBenchmark(KGNode):
    investigates: Optional[ResearchProblem] = None
    uses: Optional[MathematicalModel] = None
    evaluates: list[NumericalVariable] = field(default_factory=list)
    parameter_sets: list[ParameterSet] = field(default_factory=list)
    described_by: Optional[Publication] = None
    processing_steps: list[ProcessingStep] = field(default_factory=list)


class BenchmarkLoader:
    def __init__(self, jsonld_path: str | Path):
        self.path = Path(jsonld_path)
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        self.graph = Graph()
        self.graph.parse(str(self.path), format="json-ld")
        self._field_mapping_by_variable_id = self._build_field_mapping_index()

    @staticmethod
    def _str(uri: URIRef) -> str:
        return str(uri)

    def _label(self, subject: URIRef) -> Optional[str]:
        value = self.graph.value(subject, RDFS.label)
        return str(value) if value else None

    def _scalar(self, subject: URIRef, predicate: URIRef):
        value = self.graph.value(subject, predicate)
        if value is None:
            return None
        return value.toPython() if isinstance(value, Literal) else str(value)

    def _build_field_mapping_index(self) -> dict[str, FieldMapping]:
        mapping_by_variable_id: dict[str, FieldMapping] = {}
        for field_uri in self.graph.subjects(RDF.type, T_FIELD):
            variable_uri = self.graph.value(field_uri, REPRESENTS)
            if variable_uri is None:
                continue

            source_uri = self.graph.value(field_uri, HAS_SOURCE)
            extract_uri = self.graph.value(source_uri, HAS_EXTRACT) if source_uri else None
            file_object_uri = None
            if source_uri:
                file_object_uri = self.graph.value(source_uri, HAS_FILE_OBJECT)
                if file_object_uri is None:
                    file_object_uri = self.graph.value(source_uri, HAS_FILE_OBJECT_ALT)

            variable_id = self._str(variable_uri)
            mapping = FieldMapping(
                field_id=self._str(field_uri),
                data_type=self._scalar(field_uri, DATA_TYPE),
                source_id=self._str(source_uri) if source_uri else None,
                extract_id=self._str(extract_uri) if extract_uri else None,
                json_path=self._scalar(extract_uri, JSON_PATH) if extract_uri else None,
                file_object_id=self._str(file_object_uri) if file_object_uri else None,
                file_object_label=self._label(file_object_uri) if file_object_uri else None,
            )
            mapping_by_variable_id[variable_id] = mapping

            # Backward-compatible alias:
            # some benchmark files use field->represents "variable_*" while
            # benchmark.evaluates references "metric_*" ids for the same concept.
            if "variable_" in variable_id:
                mapping_by_variable_id[variable_id.replace("variable_", "metric_", 1)] = mapping
            elif "metric_" in variable_id:
                mapping_by_variable_id[variable_id.replace("metric_", "variable_", 1)] = mapping
        return mapping_by_variable_id

    def _field_mapping(self, variable_uri: URIRef) -> Optional[FieldMapping]:
        return self._field_mapping_by_variable_id.get(self._str(variable_uri))

    def build_numerical_parameter(self, uri: URIRef) -> NumericalParameter:
        return NumericalParameter(
            id=self._str(uri),
            label=self._label(uri),
            numerical_value=self._scalar(uri, HAS_NUMERICAL_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
            field_mapping=self._field_mapping(uri),
        )

    def build_text_parameter(self, uri: URIRef) -> TextParameter:
        return TextParameter(
            id=self._str(uri),
            label=self._label(uri),
            string_value=self._scalar(uri, HAS_STRING_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
            field_mapping=self._field_mapping(uri),
        )

    def build_numerical_variable(self, uri: URIRef) -> NumericalVariable:
        return NumericalVariable(
            id=self._str(uri),
            label=self._label(uri),
            unit=self._scalar(uri, HAS_UNIT),
            quantity_kind=self._scalar(uri, HAS_KIND_OF_QTY),
            field_mapping=self._field_mapping(uri),
        )

    def build_parameter_entry(self, uri: URIRef) -> ParameterEntry:
        if self.graph.value(uri, HAS_STRING_VALUE):
            return self.build_text_parameter(uri)
        if (uri, RDF.type, T_NUMERICAL_VARIABLE) in self.graph:
            return self.build_numerical_variable(uri)
        return self.build_numerical_parameter(uri)

    def build_parameter_set(self, uri: URIRef) -> ParameterSet:
        return ParameterSet(
            id=self._str(uri),
            label=self._label(uri),
            identifier=self._scalar(uri, M4I.identifier),
            parts=[
                self.build_parameter_entry(part)
                for part in self.graph.objects(uri, HAS_PART)
            ],
        )

    def build_tool(self, uri: URIRef) -> Tool:
        return Tool(id=self._str(uri), label=self._label(uri))

    def build_io_object(self, uri: URIRef) -> IOObject:
        return IOObject(id=self._str(uri), label=self._label(uri))

    def build_processing_step(self, uri: URIRef) -> ProcessingStep:
        return ProcessingStep(
            id=self._str(uri),
            label=self._label(uri),
            inputs=[
                self.build_io_object(input_entity)
                for input_entity in self.graph.objects(uri, HAS_INPUT)
            ],
            outputs=[
                self.build_io_object(output_entity)
                for output_entity in self.graph.objects(uri, HAS_OUTPUT)
            ],
            configurations=[
                self.build_parameter_set(config)
                for config in self.graph.objects(uri, USES_CONFIG)
            ],
            employed_tools=[
                self.build_tool(tool)
                for tool in self.graph.objects(uri, HAS_EMPLOYED_TOOL)
            ],
        )

    def load(self) -> SemanticBenchmark:
        benchmark_uri = next(self.graph.subjects(RDF.type, T_BENCHMARK), None)
        if benchmark_uri is None:
            raise ValueError("No m4i:Benchmark node found.")

        research_problem_uri = self.graph.value(benchmark_uri, INVESTIGATES)
        model_uri = self.graph.value(benchmark_uri, USES)
        publication_uri = self.graph.value(benchmark_uri, DESCRIBED_BY)

        return SemanticBenchmark(
            id=self._str(benchmark_uri),
            label=self._label(benchmark_uri),
            investigates=(
                ResearchProblem(
                    id=self._str(research_problem_uri),
                    label=self._label(research_problem_uri),
                )
                if research_problem_uri
                else None
            ),
            uses=(
                MathematicalModel(
                    id=self._str(model_uri),
                    label=self._label(model_uri),
                )
                if model_uri
                else None
            ),
            evaluates=[
                self.build_numerical_variable(metric)
                for metric in self.graph.objects(benchmark_uri, EVALUATES)
            ],
            parameter_sets=[
                self.build_parameter_set(parameter_set)
                for parameter_set in self.graph.objects(benchmark_uri, M4I.hasParameterSet)
            ],
            described_by=(
                Publication(
                    id=self._str(publication_uri),
                    label=self._label(publication_uri),
                )
                if publication_uri
                else None
            ),
            processing_steps=[
                self.build_processing_step(step)
                for step in self.graph.subjects(RDF.type, T_PROCESSING_STEP)
            ],
        )
