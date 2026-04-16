from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

M4I = Namespace("http://w3id.org/nfdi4ing/metadata4ing#")
OBO = Namespace("http://purl.obolibrary.org/obo/")

HAS_NUMERICAL_VALUE = M4I.hasNumericalValue
HAS_STRING_VALUE = M4I.hasStringValue
HAS_UNIT = M4I.hasUnit
HAS_KIND_OF_QTY = M4I.hasKindOfQuantity
HAS_PART = OBO.BFO_0000051
USES_CONFIG = M4I.usesConfiguration
HAS_EMPLOYED_TOOL = M4I.hasEmployedTool
INVESTIGATES = M4I.investigates
EVALUATES = M4I.evaluates
USES = URIRef("https://mardi4nfdi.de/mathmoddb#uses")
DESCRIBED_BY = URIRef("https://mardi4nfdi.de/mathmoddb#describedAsDocumentedBy")

T_BENCHMARK = M4I.Benchmark
T_NUMERICAL_VARIABLE = M4I.NumericalVariable
T_PROCESSING_STEP = M4I.ProcessingStep


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


@dataclass
class NumericalParameter(KGNode):
    numerical_value: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class TextParameter(KGNode):
    string_value: Optional[str] = None
    unit: Optional[str] = None


ParameterEntry = Union[NumericalParameter, TextParameter, NumericalVariable]


@dataclass
class ParameterSet(KGNode):
    parts: list[ParameterEntry] = field(default_factory=list)


@dataclass
class Tool(KGNode):
    pass


@dataclass
class ProcessingStep(KGNode):
    configurations: list[ParameterSet] = field(default_factory=list)
    employed_tools: list[Tool] = field(default_factory=list)


@dataclass
class BenchmarkSemantic(KGNode):
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

    def build_numerical_parameter(self, uri: URIRef) -> NumericalParameter:
        return NumericalParameter(
            id=self._str(uri),
            label=self._label(uri),
            numerical_value=self._scalar(uri, HAS_NUMERICAL_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
        )

    def build_text_parameter(self, uri: URIRef) -> TextParameter:
        return TextParameter(
            id=self._str(uri),
            label=self._label(uri),
            string_value=self._scalar(uri, HAS_STRING_VALUE),
            unit=self._scalar(uri, HAS_UNIT),
        )

    def build_numerical_variable(self, uri: URIRef) -> NumericalVariable:
        return NumericalVariable(
            id=self._str(uri),
            label=self._label(uri),
            unit=self._scalar(uri, HAS_UNIT),
            quantity_kind=self._scalar(uri, HAS_KIND_OF_QTY),
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
            parts=[
                self.build_parameter_entry(part)
                for part in self.graph.objects(uri, HAS_PART)
            ],
        )

    def build_tool(self, uri: URIRef) -> Tool:
        return Tool(id=self._str(uri), label=self._label(uri))

    def build_processing_step(self, uri: URIRef) -> ProcessingStep:
        return ProcessingStep(
            id=self._str(uri),
            label=self._label(uri),
            configurations=[
                self.build_parameter_set(config)
                for config in self.graph.objects(uri, USES_CONFIG)
            ],
            employed_tools=[
                self.build_tool(tool)
                for tool in self.graph.objects(uri, HAS_EMPLOYED_TOOL)
            ],
        )

    def load(self) -> BenchmarkSemantic:
        benchmark_uri = next(self.graph.subjects(RDF.type, T_BENCHMARK), None)
        if benchmark_uri is None:
            raise ValueError("No m4i:Benchmark node found.")

        research_problem_uri = self.graph.value(benchmark_uri, INVESTIGATES)
        model_uri = self.graph.value(benchmark_uri, USES)
        publication_uri = self.graph.value(benchmark_uri, DESCRIBED_BY)

        return BenchmarkSemantic(
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
